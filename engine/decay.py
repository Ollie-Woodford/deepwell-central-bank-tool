"""
Time decay layer for the central bank hawk/dove dashboard.

Each data point (statement or vote) loses weight linearly from full value on
the day it happens to zero at DECAY_DAYS (10 months). A member's stance is the
weighted average of all live points. If every point has expired, the stance is
held at its last value, which is the weighted average of the member's most
recent point(s), so the series never jumps.

Total weight of a point = decay weight x source weight x confidence x
passage weight share.
Scores run from -5 (very dovish) to +5 (very hawkish).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Optional

DECAY_DAYS = 304.0  # 10 months (10 x 30.44 days)

# How much each kind of signal counts before decay. Derived from these ratios
# (see WEIGHTING.md), with news/speculation as the unit:
#   1 dissenting vote = 1.5 votes      1 vote   = 2 speeches
#   1 speech = 1 press conference      1 speech = 1.2 comments
#   1 comment = 1 interview = 1 podcast    1 comment = 5 news/speculation
SOURCE_WEIGHTS = {
    "dissent_vote": 18.0,
    "majority_vote": 12.0,
    "speech": 6.0,
    "press_conference": 6.0,
    "testimony": 6.0,  # assumption: not in the ratios, treated as a speech
    "minutes_statement": 6.0,  # proposed: written statement in BoE minutes, treated as a speech
    "comment": 5.0,
    "interview": 5.0,
    "podcast": 5.0,
    "news_speculation": 1.0,
}

SCORE_MIN, SCORE_MAX = -5.0, 5.0


@dataclass(frozen=True)
class DataPoint:
    member_id: str
    timestamp: datetime
    score: float
    source_type: str
    confidence: float = 1.0  # 0 to 1, from the scorer
    # Share of the document's source weight carried by this passage, so a
    # document counts once in total however many passages it is split into
    # (EXTRACTION.md section 3). 1.0 for votes and single-passage documents.
    passage_weight_share: float = 1.0

    def __post_init__(self):
        if not SCORE_MIN <= self.score <= SCORE_MAX:
            raise ValueError(f"score {self.score} outside {SCORE_MIN} to {SCORE_MAX}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence {self.confidence} outside 0 to 1")
        if not 0.0 < self.passage_weight_share <= 1.0:
            raise ValueError(
                f"passage_weight_share {self.passage_weight_share} outside (0, 1]"
            )


@dataclass(frozen=True)
class Stance:
    member_id: str
    as_of: datetime
    value: Optional[float]          # None if the member has no data at all
    signal_strength: float          # sum of live weights; 0 when held
    held: bool                      # True once every point has expired
    held_since: Optional[datetime]  # when the hold began
    last_signal: Optional[datetime] # timestamp of the newest data point
    live_points: int


def decay_weight(age_days: float, decay_days: float = DECAY_DAYS) -> float:
    """Linear decay: 1.0 at age 0, 0.0 at decay_days and beyond."""
    if age_days < 0:
        return 0.0  # point is in the future relative to as_of
    return max(0.0, 1.0 - age_days / decay_days)


def base_weight(point: DataPoint, source_weights: dict = SOURCE_WEIGHTS) -> float:
    """Weight before decay: source type x confidence x passage weight share."""
    try:
        return (
            source_weights[point.source_type]
            * point.confidence
            * point.passage_weight_share
        )
    except KeyError:
        raise KeyError(
            f"unknown source_type '{point.source_type}'; "
            f"expected one of {sorted(source_weights)}"
        ) from None


def _age_days(point: DataPoint, as_of: datetime) -> float:
    return (as_of - point.timestamp).total_seconds() / 86400.0


def stance_at(
    member_id: str,
    points: Iterable[DataPoint],
    as_of: datetime,
    decay_days: float = DECAY_DAYS,
    source_weights: dict = SOURCE_WEIGHTS,
) -> Stance:
    """A member's decayed hawk/dove stance at a given moment."""
    # Only this member's points, only ones that existed by as_of, and only
    # points that carry any weight at all.
    history = [
        p for p in points
        if p.member_id == member_id
        and p.timestamp <= as_of
        and base_weight(p, source_weights) > 0
    ]

    if not history:
        return Stance(member_id, as_of, None, 0.0, False, None, None, 0)

    newest = max(p.timestamp for p in history)

    weighted_sum = 0.0
    total_weight = 0.0
    live = 0
    for p in history:
        w = decay_weight(_age_days(p, as_of), decay_days) * base_weight(p, source_weights)
        if w > 0:
            weighted_sum += w * p.score
            total_weight += w
            live += 1

    if total_weight > 0:
        return Stance(
            member_id, as_of, weighted_sum / total_weight,
            total_weight, False, None, newest, live,
        )

    # Everything has expired: hold at the last value. Just before the newest
    # point(s) expired, they were the only live points, so the last value is
    # their weighted average (decay is identical across them, so it cancels).
    latest = [p for p in history if p.timestamp == newest]
    bw = [base_weight(p, source_weights) for p in latest]
    held_value = sum(w * p.score for w, p in zip(bw, latest)) / sum(bw)
    return Stance(
        member_id, as_of, held_value, 0.0, True,
        newest + timedelta(days=decay_days), newest, 0,
    )


def momentum(
    member_id: str,
    points: Iterable[DataPoint],
    as_of: datetime,
    lookback_days: float,
    **kwargs,
) -> Optional[float]:
    """Change in stance over the lookback window (positive = more hawkish)."""
    points = list(points)
    now = stance_at(member_id, points, as_of, **kwargs).value
    then = stance_at(member_id, points, as_of - timedelta(days=lookback_days), **kwargs).value
    if now is None or then is None:
        return None
    return now - then


def timeline(
    member_id: str,
    points: Iterable[DataPoint],
    start: datetime,
    end: datetime,
    step_days: float = 1.0,
    **kwargs,
) -> list[Stance]:
    """Stance series for charting the member's movement over time."""
    points = list(points)
    out = []
    t = start
    while t <= end:
        out.append(stance_at(member_id, points, t, **kwargs))
        t += timedelta(days=step_days)
    return out
