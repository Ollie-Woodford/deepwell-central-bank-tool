from datetime import date, datetime, time
from pathlib import Path

import pytest

from pipeline import boj
from pipeline.members import load_members
from pipeline.votes import Vote, score_meeting

FIXTURES = Path(__file__).parent / "fixtures"
ALL = load_members(bank="BoJ", include_former=True)
CURRENT = load_members(bank="BoJ")


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def ids(ms):
    return sorted(m.id for m in ms)


# ---- decisions

def test_hold_with_three_dissents_and_proposals():
    d = boj.parse_decision(fixture("boj_decision_2026-04.txt"), ALL)
    assert d.rate == 0.75 and d.split == (6, 3)
    assert ids(d.voting_against) == ["nakagawa", "takata", "tamura"]
    assert d.proposals == {"nakagawa": 1.0, "takata": 1.0, "tamura": 1.0}
    assert d.ended == time(11, 57)
    rates, unknown = boj.voted_rates(d, previous=0.75)
    assert rates["takata"] == 1.0 and rates["ueda"] == 0.75 and not unknown


def test_hike_with_dissents_and_no_proposal_means_hold():
    d = boj.parse_decision(fixture("boj_decision_2026-09.txt"), ALL)
    assert d.rate == 1.25 and d.split == (7, 2)
    assert ids(d.voting_against) == ["asada", "sato"]
    rates, _ = boj.voted_rates(d, previous=1.0)
    assert rates["asada"] == rates["sato"] == 1.0
    scored = {s.member_id: s for s in score_meeting(1.0, 1.25, [Vote(k, v) for k, v in rates.items()])}
    assert scored["asada"].score == -5          # dissent against a hike
    assert scored["ueda"].score == 2            # majority backing a hike against dovish dissent


def test_absent_member_is_not_counted():
    d = boj.parse_decision(fixture("boj_decision_2026-06.txt"), ALL)
    assert ids(d.absent) == ["ueda"]
    assert "ueda" not in ids(d.voting_for)
    assert len(d.voting_for) + len(d.voting_against) == 8


def test_unanimous_ignores_votes_on_other_decisions():
    # June 2025: the guideline was unanimous; a vote against belongs to the bond purchase plan.
    d = boj.parse_decision(fixture("boj_decision_2025-06.txt"), ALL)
    assert d.split is None and d.voting_against == []
    assert len(d.voting_for) == 9


def test_spaced_out_pdf_names_still_match():
    text = fixture("boj_decision_2026-04.txt")
    assert "TAKA TA" in text or "V oting" in text  # the PDF really is split this way
    assert "takata" in ids(boj.parse_decision(text, ALL).voting_against)


def test_vote_count_mismatch_raises():
    text = fixture("boj_decision_2026-04.txt").replace("TAMURA Naoki.", "someone.")
    with pytest.raises(ValueError, match="expected the 6-3 split"):
        boj.parse_decision(text, ALL)


def test_statement_index_keeps_only_decisions():
    items = boj.parse_statement_index(fixture("boj_statement_index_2026.html"))
    assert [i.date for i in items][:2] == [date(2026, 9, 18), date(2026, 7, 31)]
    assert all(not i.title.startswith("(Reference)") for i in items)
    assert len({i.date for i in items}) == len(items)


# ---- speeches

def test_speech_index_and_attribution():
    items = boj.parse_speech_index(fixture("boj_speech_index_2026.html"))
    assert items[0].date == date(2026, 10, 15)
    who = [boj.attribute_speaker(i.speaker, CURRENT) for i in items]
    assert who[0].id == "koeda"
    kamiyama = [i for i, m in zip(items, who) if "KAMIYAMA" in i.speaker]
    assert kamiyama and all(boj.attribute_speaker(i.speaker, CURRENT) is None for i in kamiyama)


def test_parse_en_date_handles_sept():
    assert boj.parse_en_date("Sept. 10, 2026") == date(2026, 9, 10)
    assert boj.parse_en_date("June 3, 2026") == date(2026, 6, 3)


# ---- press conferences

def test_press_index_attributes_by_japanese_surname():
    items = boj.parse_press_index(fixture("boj_press_index_2026.html"), CURRENT)
    by_title = {i.title: i.member.id for i in items}
    assert by_title["小枝審議委員記者会見（10月15日）"] == "koeda"
    assert by_title["総裁定例記者会見（9月18日）"] == "ueda"
    assert by_title["総裁定例記者会見（内田副総裁代理・6月16日）"] == "uchida"
    assert by_title["佐藤審議委員就任記者会見（6月30日）"] == "sato"
    assert by_title["増審議委員記者会見（9月10日）"] == "masu"


def test_japanese_text_cleanup_and_time():
    t = boj.clean_ja_text(fixture("boj_press_2026-10-15_raw.txt"))
    assert boj.press_datetime(t) == datetime(2026, 10, 15, 14, 30, tzinfo=boj.TOKYO)
    assert "頂きます。一点は、本日" in t        # stray spaces inside sentences removed
    assert "\n\n(答)" in t                        # question and answer blocks kept apart
