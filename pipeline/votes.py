"""
Score votes by rule (docs/EXTRACTION.md, Votes). Votes never go through the
scorer.

Dissents:
  - for a move the majority did not make in that direction (a hike when the
    majority held or cut; a hold or cut when the majority hiked): +5 / -5
  - same direction as the majority's move but a different size: +3 / -3
Majority votes:
  - unanimous meeting: not recorded
  - split meeting: +2 / -2, on the opposite side to the dissenters (backing a
    hold against hike dissenters is -2; backing a hike against hold or cut
    dissenters is +2). If dissenters sat on both sides, not recorded.

Cut-side cases mirror the hike-side cases written in EXTRACTION.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

VOTE_RULE_VERSION = "vote-rule-v1"


def _sign(x: float) -> int:
    return (x > 1e-9) - (x < -1e-9)


@dataclass(frozen=True)
class Vote:
    member_id: str
    voted_rate: float


@dataclass(frozen=True)
class ScoredVote:
    member_id: str
    source_type: str          # dissent_vote or majority_vote
    score: int
    rationale: str
    voted_rate: float


def describe_move(previous: float, rate: float) -> str:
    bp = round((rate - previous) * 100)
    if bp == 0:
        return f"hold at {rate:g}%"
    return f"{'hike' if bp > 0 else 'cut'} of {abs(bp)}bp to {rate:g}%"


def score_dissent(previous: float, decision: float, voted: float) -> tuple[int, str]:
    side = _sign(voted - decision)          # +1 hawkish, -1 dovish
    majority_move = _sign(decision - previous)
    member_move = _sign(voted - previous)
    if majority_move != 0 and member_move == majority_move:
        size = "larger" if abs(voted - previous) > abs(decision - previous) else "smaller"
        return 3 * side, f"dissent for a {size} move than the majority"
    return 5 * side, f"dissent for a {describe_move(previous, voted)} against a majority {describe_move(previous, decision)}"


def score_meeting(previous: float, decision: float, votes: list[Vote]) -> list[ScoredVote]:
    """Score every recordable vote at one meeting."""
    dissents = [v for v in votes if _sign(v.voted_rate - decision) != 0]
    out = []
    for v in dissents:
        score, why = score_dissent(previous, decision, v.voted_rate)
        out.append(ScoredVote(v.member_id, "dissent_vote", score, why, v.voted_rate))

    if not dissents:
        return out  # unanimous: majority votes are not recorded

    sides = {_sign(v.voted_rate - decision) for v in dissents}
    if len(sides) != 1:
        return out  # dissent on both sides: the majority backed neither
    dissent_side = sides.pop()
    score = -2 * dissent_side
    for v in votes:
        if _sign(v.voted_rate - decision) == 0:
            why = (f"majority vote for a {describe_move(previous, decision)} at a split meeting, "
                   f"against {'hawkish' if dissent_side > 0 else 'dovish'} dissent")
            out.append(ScoredVote(v.member_id, "majority_vote", score, why, v.voted_rate))
    return out


def split_label(previous: float, decision: float, votes: list[Vote]) -> str:
    """Short label such as 'hold 6-3' for the context block."""
    kind = {1: "hike", -1: "cut", 0: "hold"}[_sign(decision - previous)]
    n_major = sum(1 for v in votes if _sign(v.voted_rate - decision) == 0)
    n_other = len(votes) - n_major
    return f"{kind} {n_major}-{n_other}" if n_other else f"{kind} unanimous"
