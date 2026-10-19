from pipeline.votes import Vote, score_dissent, score_meeting, split_label


def scores(previous, decision, rates):
    votes = [Vote(f"m{i}", r) for i, r in enumerate(rates)]
    return {(s.member_id, s.source_type): s.score for s in score_meeting(previous, decision, votes)}


def test_dissent_for_hike_against_hold_is_plus_five():
    assert score_dissent(3.75, 3.75, 4.0)[0] == 5


def test_dissent_for_cut_against_hold_is_minus_five():
    assert score_dissent(3.75, 3.75, 3.5)[0] == -5


def test_dissent_against_hike_is_minus_five():
    assert score_dissent(3.75, 4.0, 3.75)[0] == -5


def test_dissent_against_cut_is_plus_five():
    assert score_dissent(3.75, 3.5, 3.75)[0] == 5


def test_smaller_and_larger_hikes_are_three():
    assert score_dissent(3.75, 4.25, 4.0)[0] == -3   # +25 against a +50 majority
    assert score_dissent(3.75, 4.0, 4.25)[0] == 3    # +50 against a +25 majority


def test_smaller_and_larger_cuts_are_three():
    assert score_dissent(3.75, 3.25, 3.5)[0] == 3    # -25 against a -50 majority
    assert score_dissent(3.75, 3.5, 3.25)[0] == -3   # -50 against a -25 majority


def test_unanimous_meeting_records_nothing():
    assert scores(3.75, 3.75, [3.75] * 9) == {}


def test_split_hold_with_hike_dissent():
    s = scores(3.75, 3.75, [3.75] * 6 + [4.0] * 3)
    assert s[("m0", "majority_vote")] == -2
    assert s[("m8", "dissent_vote")] == 5
    assert len(s) == 9


def test_split_hike_with_hold_dissent():
    s = scores(3.75, 4.0, [4.0] * 7 + [3.75] * 2)
    assert s[("m0", "majority_vote")] == 2
    assert s[("m8", "dissent_vote")] == -5


def test_dissent_on_both_sides_skips_majority():
    s = scores(3.75, 3.75, [3.75] * 7 + [4.0, 3.5])
    assert set(s) == {("m7", "dissent_vote"), ("m8", "dissent_vote")}


def test_split_label():
    votes = [Vote("a", 3.75)] * 6 + [Vote("b", 4.0)] * 3
    assert split_label(3.75, 3.75, votes) == "hold 6-3"
    assert split_label(3.75, 3.5, [Vote("a", 3.5)] * 9) == "cut unanimous"
