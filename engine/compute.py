"""
Turn scored passages and votes into stances, momentum and timelines.

    python -m engine.compute                      # as of now
    python -m engine.compute --as-of 2026-10-19

Reads data/scores/*.jsonl (passages and votes), data/decisions/<bank>.json
and config/members.json; writes data/stances.json, which holds everything the
dashboard shows: each member's current stance, signal strength, held and
stale status, 30 and 90 day momentum, a daily stance series, every scored
point, the committee median, the last 8 votes and the newest statements.

Flagged passages (not_policy, need_context) carry no score and are left out.
Majority votes at unanimous meetings are never recorded (pipeline/votes.py),
so nothing here needs to filter them.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Optional

from engine.decay import DataPoint, momentum, stance_at, timeline
from pipeline.members import load_members
from pipeline.store import DATA, SCORES, load_decisions

OUT = DATA / "stances.json"
BANKS = ("BoE", "BoJ")
STALE_DAYS = 60       # no new signal for this long: shown faded
SERIES_START_DAYS = 300
TICKER_SIZE = 20
VOTE_STRIP = 8


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def load_records() -> list[dict]:
    out = []
    for f in sorted(SCORES.glob("[0-9]*.jsonl")):
        out += [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
    return out


def to_point(r: dict) -> DataPoint:
    return DataPoint(
        member_id=r["member_id"],
        timestamp=parse_ts(r["timestamp"]),
        score=float(r["score"]),
        source_type=r["source_type"],
        confidence=float(r.get("confidence", 1.0)),
        passage_weight_share=float(r.get("passage_weight_share", 1.0)) or 1.0,
    )


def _round(x: Optional[float], n: int = 3) -> Optional[float]:
    return None if x is None else round(x, n)


def member_summary(member, records: list[dict], as_of: datetime) -> dict:
    scored = [r for r in records if r["member_id"] == member.id and r.get("flag") is None
              and r.get("score") is not None]
    points = [to_point(r) for r in scored]
    now = stance_at(member.id, points, as_of)

    series = []
    if points:
        start = max(min(p.timestamp for p in points), as_of - timedelta(days=SERIES_START_DAYS))
        start = start.replace(hour=23, minute=59, second=0, microsecond=0)
        for s in timeline(member.id, points, start, as_of, step_days=1):
            if s.value is not None:
                series.append({"date": s.as_of.date().isoformat(), "stance": round(s.value, 3),
                               "held": s.held})

    days_since = (as_of - now.last_signal).days if now.last_signal else None
    return {
        "id": member.id,
        "name": member.name,
        "role": member.role,
        "stance": _round(now.value),
        "signal_strength": _round(now.signal_strength, 2),
        "held": now.held,
        "held_since": now.held_since.date().isoformat() if now.held_since else None,
        "last_signal": now.last_signal.isoformat().replace("+00:00", "Z") if now.last_signal else None,
        "days_since_signal": days_since,
        "stale": days_since is not None and days_since > STALE_DAYS,
        "live_points": now.live_points,
        "momentum_30d": _round(momentum(member.id, points, as_of, 30)),
        "momentum_90d": _round(momentum(member.id, points, as_of, 90)),
        "series": series,
        "points": [{
            "id": r["id"],
            "date": r["timestamp"],
            "source_type": r["source_type"],
            "score": r["score"],
            "confidence": r.get("confidence"),
            "quote": r["passage"],
            "language": r.get("language", "en"),
            "rationale": r.get("rationale", ""),
            "topics": r.get("topics", []),
            "url": r.get("document_url"),
            "institutional": r.get("institutional", False),
            "is_vote": r["source_type"].endswith("_vote"),
        } for r in sorted(scored, key=lambda r: r["timestamp"])],
    }


def vote_strip(bank: str, as_of: datetime) -> list[dict]:
    rows = [d for d in load_decisions(bank) if parse_ts(d["announced"]) <= as_of][-VOTE_STRIP:]
    out = []
    for d in rows:
        prev, rate = d["previous_rate"], d["decision_rate"]
        out.append({
            "date": d["date"], "decision_rate": rate, "previous_rate": prev,
            "label": d.get("label"), "url": d.get("url"),
            "votes": {m: {"rate": r, "dissent": abs(r - rate) > 1e-9,
                          "direction": (r > rate) - (r < rate)} for m, r in d["votes"].items()},
        })
    return out


def compute(as_of: datetime) -> dict:
    records = load_records()
    out = {"as_of": as_of.isoformat().replace("+00:00", "Z"),
           "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
           "stale_days": STALE_DAYS, "banks": {}}
    for bank in BANKS:
        members = load_members(bank=bank)
        bank_records = [r for r in records if r["bank"] == bank and parse_ts(r["timestamp"]) <= as_of]
        summaries = [member_summary(m, bank_records, as_of) for m in members]
        stances = [s["stance"] for s in summaries if s["stance"] is not None]
        passages = sorted((r for r in bank_records if not r["source_type"].endswith("_vote")
                           and r.get("flag") is None), key=lambda r: r["timestamp"], reverse=True)
        out["banks"][bank] = {
            "members": summaries,
            "median": _round(median(stances)) if stances else None,
            "votes": vote_strip(bank, as_of),
            "ticker": [{"member_id": r["member_id"], "date": r["timestamp"], "score": r["score"],
                        "quote": r["passage"], "source_type": r["source_type"], "url": r.get("document_url"),
                        "topics": r.get("topics", [])}
                       for r in passages[:TICKER_SIZE]],
            "scored_passages": len(passages),
            "votes_recorded": sum(1 for r in bank_records if r["source_type"].endswith("_vote")),
        }
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", help="YYYY-MM-DD (end of day UTC); default now")
    args = ap.parse_args(argv)
    if args.as_of:
        as_of = datetime.fromisoformat(args.as_of).replace(hour=23, minute=59, tzinfo=timezone.utc)
    else:
        as_of = datetime.now(timezone.utc).replace(microsecond=0)
    result = compute(as_of)
    OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    boe = result["banks"]["BoE"]
    print(f"Wrote {OUT.name} as of {result['as_of']}: BoE median {boe['median']}, "
          f"{boe['scored_passages']} passages, {boe['votes_recorded']} votes")
    for m in sorted(boe["members"], key=lambda m: m["stance"] if m["stance"] is not None else -99):
        print(f"  {m['name']:<20} {m['stance']:+.2f}  30d {m['momentum_30d'] or 0:+.2f}  "
              f"90d {m['momentum_90d'] or 0:+.2f}  strength {m['signal_strength']:.1f}"
              f"{'  STALE' if m['stale'] else ''}{'  HELD' if m['held'] else ''}")


if __name__ == "__main__":
    main()
