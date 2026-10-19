"""
The context block every passage is scored against (rubric.md section 2):

    Bank:                 BoE
    Date:                 2026-09-24
    Policy rate:          3.75%
    Last decision:        hold, 6-3 (3 for a hike)
    Market-implied path:  +97bp over 12 months (from baseline_2026-09-21.json)
    Speaker's last vote:  hold

Decisions count from the moment they are announced. A written statement in the
minutes is published with its meeting's decision, so it gets that decision and
the speaker's vote at that meeting.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .store import DATA, load_decisions

BASELINE_DIR = DATA / "baseline"


def _move(previous: float, rate: float) -> str:
    bp = round((rate - previous) * 100)
    if bp == 0:
        return "hold"
    return f"{'hike' if bp > 0 else 'cut'} to {rate:g}%"


def decision_label(d: dict) -> str:
    """'hold, 6-3 (3 for a hike)' or 'hike to 4%, unanimous'."""
    prev, rate = d["previous_rate"], d["decision_rate"]
    kind = _move(prev, rate)
    votes = list(d["votes"].values())
    majority = sum(1 for r in votes if abs(r - rate) < 1e-9)
    others = [r for r in votes if abs(r - rate) >= 1e-9]
    if not others:
        return f"{kind}, unanimous"
    groups: dict[str, int] = {}
    for r in others:
        groups[_move(prev, r)] = groups.get(_move(prev, r), 0) + 1
    detail = ", ".join(f"{n} for a {m.split(' to ')[0]}" if m != "hold" else f"{n} for a hold"
                       for m, n in groups.items())
    return f"{kind}, {majority}-{len(others)} ({detail})"


def last_decision(bank: str, before_iso: str, decisions: Optional[list] = None) -> Optional[dict]:
    rows = decisions if decisions is not None else load_decisions(bank)
    earlier = [d for d in rows if d["announced"] <= before_iso]
    return earlier[-1] if earlier else None


def last_vote(member_id: str, bank: str, before_iso: str, decisions: Optional[list] = None) -> Optional[str]:
    rows = decisions if decisions is not None else load_decisions(bank)
    for d in reversed([d for d in rows if d["announced"] <= before_iso]):
        if member_id in d["votes"]:
            return _move(d["previous_rate"], d["votes"][member_id])
    return None


def baseline_for(bank: str, date_iso: str, baseline_dir: Path = BASELINE_DIR) -> Optional[tuple[str, dict]]:
    """The most recent baseline file dated on or before the statement."""
    files = sorted(baseline_dir.glob("baseline_*.json"))
    usable = [f for f in files if f.stem.removeprefix("baseline_") <= date_iso[:10]]
    for f in reversed(usable):
        data = json.loads(f.read_text())
        if bank in data:
            return f.name, data[bank]
    return None


def build_context(bank: str, member_id: str, timestamp_iso: str,
                  decisions: Optional[list] = None, baseline_dir: Path = BASELINE_DIR) -> dict:
    d = last_decision(bank, timestamp_iso, decisions)
    base = baseline_for(bank, timestamp_iso, baseline_dir)
    return {
        "bank": bank,
        "date": timestamp_iso[:10],
        "policy_rate": d["decision_rate"] if d else None,
        "last_decision": decision_label(d) if d else None,
        "last_decision_date": d["date"] if d else None,
        "market_implied_12m_bp": base[1]["priced_change_12m_bp"] if base else None,
        "baseline_file": base[0] if base else None,
        "speaker_last_vote": last_vote(member_id, bank, timestamp_iso, decisions),
    }


def context_block(ctx: dict) -> str:
    def or_na(v, fmt=str):
        return fmt(v) if v is not None else "not available"
    path = (f"{ctx['market_implied_12m_bp']:+d}bp over 12 months (from {ctx['baseline_file']})"
            if ctx["baseline_file"] else "not available (no baseline dated on or before this statement)")
    decision = (f"{ctx['last_decision']} on {ctx['last_decision_date']}"
                if ctx["last_decision"] else "not available")
    return "\n".join([
        f"Bank:                 {ctx['bank']}",
        f"Date:                 {ctx['date']}",
        f"Policy rate:          {or_na(ctx['policy_rate'], lambda r: f'{r:g}%')}",
        f"Last decision:        {decision}",
        f"Market-implied path:  {path}",
        f"Speaker's last vote:  {or_na(ctx['speaker_last_vote'])}",
    ])
