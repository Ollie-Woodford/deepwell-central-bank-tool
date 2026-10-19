"""
Check scored records against the schema before anything is committed.

    python -m pipeline.validate                                    # every file in data/scores/
    python -m pipeline.validate --append data/scores/incoming.jsonl

With --append, the incoming file is checked together with what is already
stored (ids must be new, document weight shares must sum to 1). If every record
passes, they are appended to their month's file and the incoming file is
deleted. If any fails, nothing is written.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from engine.decay import SCORE_MAX, SCORE_MIN, SOURCE_WEIGHTS

from .members import load_members, normalise_name
from .pending import rubric_version
from .store import RAW, SCORES, append_scores
from .votes import VOTE_RULE_VERSION

VOTE_TYPES = {"dissent_vote", "majority_vote"}
FLAGS = {None, "not_policy", "need_context"}
UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

COMMON = {
    "id": str, "member_id": str, "bank": str, "timestamp": str, "source_type": str,
    "document_url": str, "passage": str, "language": str, "context": dict,
    "confidence": (int, float), "rationale": str, "rubric_version": str,
    "passage_weight_share": (int, float),
}
PASSAGE = {
    "document_id": str, "rate_path_signal": str, "dimensions": dict, "topics": list,
    "key_quote": str, "institutional": bool, "novelty": str,
}


def _squash(s: str) -> str:
    """Compare passages to documents ignoring spacing, quote style and case."""
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


class Checker:
    def __init__(self):
        self.members = {m.id: m for m in load_members()}
        self.version = rubric_version()
        self._doc_text: dict[str, str] = {}

    def doc_text(self, doc_id: str, bank: str):
        if doc_id not in self._doc_text:
            path = RAW / bank.lower() / f"{doc_id}.json"
            self._doc_text[doc_id] = _squash(json.loads(path.read_text())["text"]) if path.exists() else None
        return self._doc_text[doc_id]

    def check(self, r: dict) -> list[str]:
        errs = []
        is_vote = r.get("source_type") in VOTE_TYPES
        schema = dict(COMMON, **({} if is_vote else PASSAGE))
        for k, t in schema.items():
            if k not in r:
                errs.append(f"missing {k}")
            elif not isinstance(r[k], t) or isinstance(r[k], bool) and t is not bool:
                errs.append(f"{k} has type {type(r[k]).__name__}")
        if errs:
            return errs

        m = self.members.get(r["member_id"])
        if m is None:
            errs.append(f"unknown member_id {r['member_id']}")
        elif m.bank != r["bank"]:
            errs.append(f"{r['member_id']} is not a {r['bank']} member")
        if not UTC.match(r["timestamp"]):
            errs.append("timestamp must be UTC like 2026-09-24T08:00:00Z")
        if r["source_type"] not in SOURCE_WEIGHTS:
            errs.append(f"unknown source_type {r['source_type']}")
        if not 0 <= r["confidence"] <= 1:
            errs.append("confidence outside 0 to 1")
        if not r["passage"].strip():
            errs.append("empty passage")

        flag, score = r.get("flag"), r.get("score")
        if flag not in FLAGS:
            errs.append(f"flag {flag!r} not one of {sorted(f for f in FLAGS if f)} or null")
        if flag is None:
            if not isinstance(score, int) or isinstance(score, bool):
                errs.append("score must be a whole number when flag is null")
            elif not SCORE_MIN <= score <= SCORE_MAX:
                errs.append(f"score {score} outside {SCORE_MIN:g} to {SCORE_MAX:g}")
            if not 0 < r["passage_weight_share"] <= 1:
                errs.append("passage_weight_share must be above 0 and at most 1 for a scored passage")
        else:
            if score is not None:
                errs.append("score must be null when flag is set")
            if r["passage_weight_share"] != 0:
                errs.append("passage_weight_share must be 0 when flag is set")

        if is_vote:
            if r["rubric_version"] != VOTE_RULE_VERSION:
                errs.append(f"vote rubric_version must be {VOTE_RULE_VERSION}")
            return errs

        if r["rubric_version"] != self.version:
            errs.append(f"rubric_version {r['rubric_version']} but rubric.md is {self.version}")
        if r["rate_path_signal"] not in ("explicit", "implied", "none"):
            errs.append("rate_path_signal must be explicit, implied or none")
        if r["novelty"] not in ("new", "repeated"):
            errs.append("novelty must be new or repeated")
        if isinstance(score, int) and abs(score) == 5 and r["rate_path_signal"] != "explicit":
            errs.append("+/-5 outside a vote needs an explicit call for a move (rubric rule 6)")
        for k, v in r["dimensions"].items():
            if v is not None and (not isinstance(v, int) or not SCORE_MIN <= v <= SCORE_MAX):
                errs.append(f"dimension {k} must be a whole number from -5 to 5 or null")
        if not all(isinstance(t, str) for t in r["topics"]):
            errs.append("topics must be strings")
        if len(r["key_quote"].split()) > 40:
            errs.append("key_quote over 40 words")
        if not r["id"].startswith(r["document_id"]):
            errs.append("id must start with document_id")
        if flag != "not_policy" or r["passage_weight_share"] != 0:
            text = self.doc_text(r["document_id"], r["bank"])
            if text is None:
                errs.append(f"document {r['document_id']} not found in data/raw")
            elif _squash(r["passage"]) not in text:
                errs.append("passage is not verbatim from the document")
        return errs


def read_jsonl(path: Path) -> list[dict]:
    out = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"{path.name} line {n}: not JSON ({e})") from None
    return out


def validate(existing: list[dict], incoming: list[dict]) -> list[str]:
    """Errors for incoming records, checked in the context of existing ones."""
    checker = Checker()
    errors = []
    seen = {r["id"] for r in existing}
    for i, r in enumerate(incoming, 1):
        rid = r.get("id", f"record {i}")
        if rid in seen:
            errors.append(f"{rid}: duplicate id")
        seen.add(rid)
        errors += [f"{rid}: {e}" for e in checker.check(r)]

    shares = defaultdict(float)
    for r in existing + incoming:
        if r.get("document_id") and r.get("rubric_version") == checker.version and r.get("flag") is None:
            shares[r["document_id"]] += r.get("passage_weight_share", 0)
    for doc in {r.get("document_id") for r in incoming if r.get("document_id")}:
        if doc in shares and abs(shares[doc] - 1) > 0.001:
            errors.append(f"{doc}: passage weight shares sum to {shares[doc]:.4f}, not 1")
    return errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--append", type=Path, help="incoming JSONL file to check and append")
    args = ap.parse_args(argv)

    stored_files = sorted(SCORES.glob("[0-9]*.jsonl"))
    if args.append:
        existing = [r for f in stored_files for r in read_jsonl(f)]
        incoming = read_jsonl(args.append)
        errors = validate(existing, incoming)
    else:
        incoming = [r for f in stored_files for r in read_jsonl(f)]
        errors = validate([], incoming)

    if errors:
        print(f"{len(errors)} problem(s); nothing written:" if args.append else f"{len(errors)} problem(s):")
        print("\n".join(f"  {e}" for e in errors))
        return 1
    if args.append:
        n = append_scores(incoming)
        args.append.unlink()
        print(f"OK: {n} records appended.")
    else:
        print(f"OK: {len(incoming)} records valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
