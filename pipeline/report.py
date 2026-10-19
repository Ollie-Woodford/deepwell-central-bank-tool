"""
Markdown list of collected documents and votes, for checking collection.

    python -m pipeline.report --bank BoE --since 2026-07-19 > reports/boe_collection.md
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date

from .members import load_members
from .store import RAW, SCORES, STATE_FILE


def build(bank: str, since: date) -> str:
    names = {m.id: m.name for m in load_members(bank=bank)}
    docs = [json.loads(f.read_text(encoding="utf-8")) for f in (RAW / bank.lower()).glob("*.json")]
    docs = sorted((d for d in docs if d["published"][:10] >= since.isoformat()),
                  key=lambda d: (d["published"], d["member_id"]))
    votes = []
    for f in sorted(SCORES.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["bank"] == bank and r["source_type"].endswith("_vote") and r["timestamp"][:10] >= since.isoformat():
                votes.append(r)

    out = [f"# {bank} collection since {since}", ""]
    speeches = [d for d in docs if d["kind"] == "speech"]
    statements = [d for d in docs if d["kind"] == "minutes_statement"]
    out += [f"{len(speeches)} speeches, {len(statements)} written statements in minutes, "
            f"{len(votes)} votes recorded.", ""]

    out += ["## Speeches", "", "| Published (UTC) | Member | Type (first guess) | Title | Text | Length |",
            "|---|---|---|---|---|---|"]
    for d in speeches:
        out.append(f"| {d['published'][:16].replace('T', ' ')} | {names.get(d['member_id'], d['member_id'])} "
                   f"| {d['source_type_hint']} | [{d['title']}]({d['url']}) | {d['text_source']} "
                   f"| {len(d['text']):,} chars |")

    out += ["", "## Votes and written statements by meeting", ""]
    by_meeting = defaultdict(list)
    for v in votes:
        by_meeting[(v["timestamp"][:10], v["document_url"])].append(v)
    stmt_by_meeting = defaultdict(dict)
    for d in statements:
        stmt_by_meeting[d["published"][:10]][d["member_id"]] = d
    for day in sorted(set(stmt_by_meeting) | {k[0] for k in by_meeting}):
        url = next((u for (dd, u) in by_meeting if dd == day), None) or next(iter(stmt_by_meeting[day].values()))["url"]
        vs = {v["member_id"]: v for (dd, _), lst in by_meeting.items() if dd == day for v in lst}
        label = next(iter(vs.values()))["context"]["last_decision"] if vs else "unanimous (no votes recorded)"
        out += [f"### [{day}]({url}): {label}", "",
                "| Member | Voted for | Recorded as | Score | Statement |", "|---|---|---|---|---|"]
        members = sorted(set(vs) | set(stmt_by_meeting[day]), key=lambda m: names.get(m, m))
        for m in members:
            v = vs.get(m)
            st = stmt_by_meeting[day].get(m)
            voted = f"{(v or st)['vote']['voted_rate']:g}%"
            rec = v["source_type"] if v else "not recorded"
            score = f"{v['score']:+d}" if v else ""
            out.append(f"| {names.get(m, m)} | {voted} | {rec} | {score} | "
                       f"{len(st['text']):,} chars |" if st else "| | | | | |")
        out.append("")

    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {"seen": {}}
    dropped = sorted(v["note"] for v in state["seen"].values() if v["note"])
    if dropped:
        out += ["## Feed items checked and dropped", ""] + [f"- {n}" for n in dropped] + [""]
    return "\n".join(out)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", default="BoE")
    ap.add_argument("--since", type=date.fromisoformat, required=True)
    args = ap.parse_args(argv)
    print(build(args.bank, args.since))


if __name__ == "__main__":
    main()
