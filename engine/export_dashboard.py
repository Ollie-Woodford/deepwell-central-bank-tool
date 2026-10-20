"""
Flatten data/stances.json into the tables the dashboard reads.

    python -m engine.export_dashboard

Writes data/dashboard/{members,series,points,votes}.json, each an array of row
objects covering both banks (a `bank` column tells them apart). The dashboard
artifact holds these as its datasets; a routine refreshes them by uploading new
copies (see CLAUDE.md, Phase 4).
"""

from __future__ import annotations

import argparse
import json

from pipeline.store import DATA

STANCES = DATA / "stances.json"
OUT_DIR = DATA / "dashboard"


def export(bank: str) -> dict[str, list[dict]]:
    data = json.loads(STANCES.read_text())
    b = data["banks"][bank]
    members, series, points, votes = [], [], [], []
    for m in b["members"]:
        row = {k: m[k] for k in (
            "id", "name", "role", "stance", "signal_strength", "held", "held_since", "last_signal",
            "days_since_signal", "stale", "live_points", "momentum_30d", "momentum_90d")}
        # Rounded to what the page shows, so its figures match the data exactly.
        for k, n in (("stance", 2), ("momentum_30d", 2), ("momentum_90d", 2), ("signal_strength", 1)):
            row[k] = None if row[k] is None else round(row[k], n)
        members.append(row | {"as_of": data["as_of"], "bank": bank})
        series += [{"bank": bank, "member_id": m["id"], "date": s["date"], "stance": s["stance"], "held": s["held"]}
                   for s in m["series"]]
        points += [{
            "id": p["id"], "bank": bank, "member_id": m["id"], "date": p["date"], "source_type": p["source_type"],
            "score": p["score"], "confidence": p["confidence"], "quote": p["quote"],
            "rationale": p["rationale"], "topics": ",".join(p["topics"]), "url": p["url"],
            "is_vote": p["is_vote"], "institutional": p["institutional"],
        } for p in m["points"]]
    for d in b["votes"]:
        for mid, v in d["votes"].items():
            votes.append({"key": f"{bank}|{d['date']}|{mid}", "bank": bank, "date": d["date"], "member_id": mid,
                          "rate": v["rate"], "decision_rate": d["decision_rate"],
                          "previous_rate": d["previous_rate"], "dissent": v["dissent"],
                          "direction": v["direction"], "label": d["label"], "url": d["url"]})
    return {"members": members, "series": series, "points": points, "votes": votes}


def main(argv=None) -> None:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tables: dict[str, list[dict]] = {}
    for bank in ("BoE", "BoJ"):
        for name, rows in export(bank).items():
            tables.setdefault(name, []).extend(rows)
    for name, rows in tables.items():
        path = OUT_DIR / f"{name}.json"
        path.write_text(json.dumps(rows, ensure_ascii=False) + "\n")
        print(f"{path.relative_to(DATA.parent)}: {len(rows)} rows, {path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
