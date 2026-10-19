from datetime import datetime, timedelta

import pytest

from decay import (
    DECAY_DAYS, SOURCE_WEIGHTS, DataPoint, base_weight, decay_weight,
    momentum, stance_at, timeline,
)

T0 = datetime(2026, 1, 1, 12, 0)


def day(n):
    return T0 + timedelta(days=n)


def pill_points():
    return [
        DataPoint("pill", day(0), 3.0, "speech"),
        DataPoint("pill", day(120), -1.0, "speech"),
    ]


def test_decay_weight_is_linear_over_ten_months():
    assert decay_weight(0) == 1.0
    assert decay_weight(DECAY_DAYS / 2) == pytest.approx(0.5)
    assert decay_weight(DECAY_DAYS) == 0.0
    assert decay_weight(DECAY_DAYS + 50) == 0.0
    assert decay_weight(-1) == 0.0


def test_recent_point_dominates_as_older_one_fades():
    pts = pill_points()
    s150 = stance_at("pill", pts, day(150)).value
    s300 = stance_at("pill", pts, day(300)).value
    assert -1.0 < s300 < s150 < 3.0


def test_only_newest_point_left_after_older_expires():
    s = stance_at("pill", pill_points(), day(350))
    assert s.value == pytest.approx(-1.0)
    assert not s.held and s.live_points == 1


def test_holds_last_value_after_everything_expires():
    s = stance_at("pill", pill_points(), day(500))
    assert s.held
    assert s.value == pytest.approx(-1.0)
    assert s.signal_strength == 0.0
    assert s.held_since == day(120) + timedelta(days=DECAY_DAYS)


def test_no_jump_at_moment_of_hold():
    pts = pill_points()
    expiry = day(120) + timedelta(days=DECAY_DAYS)
    before = stance_at("pill", pts, expiry - timedelta(minutes=1))
    after = stance_at("pill", pts, expiry + timedelta(minutes=1))
    assert not before.held and after.held
    assert before.value == pytest.approx(after.value)


def test_held_value_blends_points_on_same_newest_timestamp():
    pts = [
        DataPoint("ueda", day(0), 2.0, "press_conference"),   # weight 6
        DataPoint("ueda", day(0), -1.0, "news_speculation"),  # weight 1
    ]
    s = stance_at("ueda", pts, day(400))
    assert s.held
    assert s.value == pytest.approx((2.0 * 6 - 1.0 * 1) / 7)


def test_weights_match_stated_ratios():
    w = SOURCE_WEIGHTS
    assert w["dissent_vote"] == pytest.approx(1.5 * w["majority_vote"])
    assert w["majority_vote"] == pytest.approx(2 * w["speech"])
    assert w["speech"] == pytest.approx(w["press_conference"])
    assert w["speech"] == pytest.approx(w["minutes_statement"])
    assert w["speech"] == pytest.approx(1.2 * w["comment"])
    assert w["comment"] == w["interview"] == w["podcast"]
    assert w["comment"] == pytest.approx(5 * w["news_speculation"])


def test_passage_shares_make_a_document_count_once():
    # A speech split into 4 passages carries the same total weight as a
    # single-passage speech, so it pulls the stance no harder.
    split = [DataPoint("mann", day(0), 3.0, "speech", passage_weight_share=0.25)
             for _ in range(4)]
    assert sum(base_weight(p) for p in split) == pytest.approx(SOURCE_WEIGHTS["speech"])
    other = [DataPoint("mann", day(0), -3.0, "speech")]
    assert stance_at("mann", split + other, day(10)).value == pytest.approx(0.0)


def test_out_of_range_passage_share_rejected():
    for share in (0.0, -0.5, 1.5):
        with pytest.raises(ValueError):
            DataPoint("pill", day(0), 1.0, "speech", passage_weight_share=share)


def test_dissent_outweighs_speech():
    pts = [
        DataPoint("asada", day(0), -4.0, "dissent_vote"),
        DataPoint("asada", day(0), 1.0, "speech"),
    ]
    assert stance_at("asada", pts, day(10)).value < -1.5


def test_future_points_and_other_members_ignored():
    pts = pill_points() + [DataPoint("mann", day(10), 5.0, "speech")]
    assert stance_at("pill", pts, day(60)).value == pytest.approx(3.0)


def test_no_data_returns_none():
    s = stance_at("greene", pill_points(), day(10))
    assert s.value is None and not s.held


def test_momentum_zero_when_held_and_negative_when_turning_dovish():
    pts = pill_points()
    assert momentum("pill", pts, day(600), 90) == pytest.approx(0.0)
    assert momentum("pill", pts, day(130), 30) < 0


def test_unknown_source_type_rejected():
    with pytest.raises(KeyError):
        stance_at("pill", [DataPoint("pill", day(0), 1.0, "tweet")], day(1))


def test_out_of_range_score_rejected():
    with pytest.raises(ValueError):
        DataPoint("pill", day(0), 7.0, "speech")


def test_timeline_is_continuous():
    series = timeline("pill", pill_points(), day(0), day(600))
    values = [s.value for s in series]
    jumps = [abs(b - a) for a, b in zip(values, values[1:])]
    # Largest daily move is the day the second statement lands; nothing else jumps.
    assert sorted(jumps)[-2] < 0.05
