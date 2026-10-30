from datetime import date
from pathlib import Path

from pipeline import fed
from pipeline.context import decision_label
from pipeline.members import load_members
from pipeline.votes import Vote, score_meeting, split_label

FIX = Path(__file__).parent / "fixtures" / "fed"
MEMBERS = load_members(bank="Fed", include_former=True)


def _statement(name):
    return fed.parse_statement((FIX / f"{name}.htm").read_text(encoding="utf-8"))


def test_parse_number():
    assert fed.parse_number("3-1/2") == 3.5
    assert fed.parse_number("3‑3/4") == 3.75
    assert fed.parse_number("3¾") == 3.75
    assert fed.parse_number("1/4") == 0.25
    assert fed.parse_number("4") == 4.0


def test_old_format_lists_every_voter_and_guidance_dissents():
    st = _statement("monetary20260429a")
    assert (st.previous_rate, st.decision_rate, st.low) == (3.75, 3.75, 3.5)
    mv = fed.meeting_votes(st, date(2026, 4, 29), MEMBERS)
    assert not mv.unmatched
    assert len(mv.rates) == 12
    assert mv.rates["miran"] == 3.5
    assert mv.guidance == {"hammack": 1, "kashkari": 1, "logan": 1}
    votes = [Vote(m, r) for m, r in mv.rates.items()]
    assert split_label(3.75, 3.75, votes, mv.guidance) == "hold 8-4"
    scored = {s.member_id: s.score for s in score_meeting(3.75, 3.75, votes, mv.guidance)}
    # Dissent on both sides, so the majority is not recorded.
    assert scored == {"miran": -5, "hammack": 3, "kashkari": 3, "logan": 3}


def test_new_format_names_only_dissenters():
    st = _statement("monetary20261028a")
    assert st.tally == (10, 2)
    mv = fed.meeting_votes(st, date(2026, 10, 28), MEMBERS)
    assert not mv.unmatched
    assert mv.rates["cook"] == mv.rates["hammack"] == 4.25
    assert mv.rates["warsh"] == 4.0
    assert "miran" not in mv.rates


def test_hike_statement():
    st = _statement("monetary20260916a")
    assert (st.previous_rate, st.decision_rate) == (3.75, 4.0)
    mv = fed.meeting_votes(st, date(2026, 9, 16), MEMBERS)
    assert len(mv.rates) == 12 and not st.dissents


def test_voters_and_chair_change_in_may():
    assert "miran" in fed.voters_on(date(2026, 3, 18)) and "warsh" not in fed.voters_on(date(2026, 3, 18))
    assert "warsh" in fed.voters_on(date(2026, 6, 17)) and "miran" not in fed.voters_on(date(2026, 6, 17))
    assert fed.chair_on(date(2026, 4, 29)) == "powell"
    assert fed.chair_on(date(2026, 6, 17)) == "warsh"


def test_chair_remarks_drop_reporters():
    transcript = (
        "October 28, 2026 Chairman Warsh’s Press Conference PRELIMINARY\n"
        "CHAIRMAN WARSH. Good day.\nThe Committee will deliver\nprice stability.\n"
        "MICHELLE SMITH. Colby.\nCOLBY SMITH. Will you hike in December?\n"
        "Page 3 of 20\n"
        "CHAIRMAN WARSH. I don’t prejudge meetings.\n")
    out = fed.chair_remarks(transcript)
    assert out == "Good day. The Committee will deliver price stability.\n\nI don’t prejudge meetings."


def test_decision_label_shows_range_and_guidance():
    d = {"previous_rate": 3.75, "decision_rate": 3.75, "range": [3.5, 3.75],
         "votes": {"a": 3.75, "b": 3.75, "c": 3.5}, "guidance_dissents": {"b": 1}}
    assert decision_label(d) == "hold, 1-2 (1 for a cut, 1 against an easing bias)"
    d2 = {"previous_rate": 3.75, "decision_rate": 4.0, "range": [3.75, 4.0], "votes": {"a": 4.0}}
    assert decision_label(d2) == "hike to 3.75 to 4%, unanimous"
