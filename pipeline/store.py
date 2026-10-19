"""
Where collected material lives.

data/raw/<bank>/<doc id>.json   one file per document (speech, minutes statement)
data/scores/YYYY-MM.jsonl       scored data points; votes are written here by rule
data/decisions/<bank>.json      every policy decision with each member's vote, for context blocks
data/state.json                 what has been seen, so each run only fetches new items
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
SCORES = DATA / "scores"
STATE_FILE = DATA / "state.json"
DECISIONS = DATA / "decisions"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class State:
    """
    {"seen": {key: {"first_seen": ..., "doc_id": ... or null, "note": ...}}}

    Keys are source URLs for feed items and minutes pages. doc_id is null for
    items that were checked and dropped (for example a speech by a non-member).
    """

    def __init__(self, path: Path = STATE_FILE):
        self.path = path
        self.data = json.loads(path.read_text()) if path.exists() else {"seen": {}}

    def seen(self, key: str) -> bool:
        return key in self.data["seen"]

    def mark(self, key: str, doc_ids=None, note: str = "") -> None:
        self.data["seen"][key] = {"first_seen": utc_now_iso(), "doc_ids": doc_ids or [], "note": note}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=1, ensure_ascii=False, sort_keys=True) + "\n")


def write_raw(doc: dict, raw_dir: Path = RAW) -> Path:
    path = raw_dir / doc["bank"].lower() / f"{doc['id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    return path


def existing_score_ids(scores_dir: Path = SCORES) -> set[str]:
    ids = set()
    for f in scores_dir.glob("[0-9]*.jsonl"):  # monthly files only, never incoming.jsonl
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                ids.add(json.loads(line)["id"])
    return ids


def append_scores(records: list[dict], scores_dir: Path = SCORES) -> int:
    """Append records to their month's file, skipping ids already stored."""
    have = existing_score_ids(scores_dir)
    new = [r for r in records if r["id"] not in have]
    scores_dir.mkdir(parents=True, exist_ok=True)
    for r in new:
        with open(scores_dir / f"{r['timestamp'][:7]}.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(new)


def load_decisions(bank: str, decisions_dir: Path = DECISIONS) -> list[dict]:
    path = decisions_dir / f"{bank.lower()}.json"
    return json.loads(path.read_text()) if path.exists() else []


def save_decision(decision: dict, decisions_dir: Path = DECISIONS) -> None:
    """Add or replace the decision for its bank and date, keeping the file sorted."""
    rows = [d for d in load_decisions(decision["bank"], decisions_dir) if d["date"] != decision["date"]]
    rows.append(decision)
    rows.sort(key=lambda d: d["date"])
    decisions_dir.mkdir(parents=True, exist_ok=True)
    (decisions_dir / f"{decision['bank'].lower()}.json").write_text(
        json.dumps(rows, indent=1, ensure_ascii=False) + "\n")
