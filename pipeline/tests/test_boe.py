from datetime import date
from pathlib import Path

import pytest

from pipeline import boe
from pipeline.members import load_members, match_name, normalise_name

FIXTURES = Path(__file__).parent / "fixtures"
MEMBERS = load_members(bank="BoE")


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def votes_by_member(minutes):
    return {v.member.id: v.voted_rate for v in minutes.votes}


# ---- members

def test_name_matching_uses_full_names_only():
    assert match_name("Catherine L Mann", MEMBERS).id == "mann"
    assert match_name("Professor Alan Taylor", MEMBERS).id == "taylor"
    assert match_name("David Bailey", MEMBERS) is None  # PRA, not the Governor
    assert match_name("Bailey", MEMBERS) is None


def test_normalise_name_strips_accents_and_titles():
    assert normalise_name("Dr  Swati Dhingra") == "swati dhingra"
    assert normalise_name("Nathanaël Benjamin") == "nathanael benjamin"


# ---- minutes

def test_september_minutes_votes_and_statements():
    m = boe.parse_minutes(fixture("boe_minutes_2026-09.html"), MEMBERS)
    assert m.meeting_end == date(2026, 9, 16)
    assert (m.previous_rate, m.decision_rate) == (3.75, 3.75)
    assert votes_by_member(m) == {
        "bailey": 3.75, "breeden": 3.75, "dhingra": 3.75, "lombardelli": 3.75,
        "ramsden": 3.75, "taylor": 3.75, "greene": 4.0, "mann": 4.0, "pill": 4.0,
    }
    assert not m.unmatched
    pill = next(v for v in m.votes if v.member.id == "pill")
    assert pill.statement.startswith("A 25-basis point increase in Bank Rate")


def test_colon_outside_bold_name_is_parsed():
    # September has "<strong>Sarah Breeden</strong>: ..." as well as "<strong>Name:</strong>"
    m = boe.parse_minutes(fixture("boe_minutes_2026-09.html"), MEMBERS)
    breeden = next(v for v in m.votes if v.member.id == "breeden")
    assert breeden.statement.startswith("The near-term outlook")


def test_february_minutes_cut_dissent():
    m = boe.parse_minutes(fixture("boe_minutes_2026-02.html"), MEMBERS)
    v = votes_by_member(m)
    assert len(v) == 9
    assert {k for k, r in v.items() if r == 3.5} == {"breeden", "dhingra", "ramsden", "taylor"}


def test_unanimous_minutes():
    m = boe.parse_minutes(fixture("boe_minutes_2026-03.html"), MEMBERS)
    assert set(votes_by_member(m).values()) == {3.75}
    assert len(m.votes) == 9


def test_missing_member_raises():
    html = fixture("boe_minutes_2026-09.html").replace("<strong>Huw Pill</strong>:", "Huw Pill said")
    with pytest.raises(ValueError, match="expected 9"):
        boe.parse_minutes(html, MEMBERS)


def test_minutes_url_and_release_time():
    d = date(2026, 9, 17)
    assert boe.minutes_url(d).endswith("/2026/september-2026")
    assert boe.minutes_release_time(d).utcoffset().total_seconds() == 3600  # BST


# ---- speeches

def test_feed_parses_fifty_items():
    items = boe.parse_feed(fixture("boe_speeches_feed.xml"))
    assert len(items) == 50
    assert items[0].published.tzinfo is not None


def test_html_speech_attributed_by_bio_link():
    items = boe.parse_feed(fixture("boe_speeches_feed.xml"))
    page = boe.parse_speech_page(fixture("boe_speech_bailey_html.html"))
    item = next(i for i in items if "Financial resilience" in i.title)
    assert boe.attribute_speech(item, page, MEMBERS).id == "bailey"
    assert not boe.needs_pdf(page)
    paras = [p for p in page.html_text.split("\n\n") if len(p) > 40]
    assert len(paras) == len(set(paras)), "nested content blocks duplicated text"


def test_pdf_speech_without_name_in_title():
    items = boe.parse_feed(fixture("boe_speeches_feed.xml"))
    item = items[0]  # Jackson Hole paper; title names nobody
    page = boe.parse_speech_page(fixture("boe_speech_mann_pdf.html"))
    assert boe.attribute_speech(item, page, MEMBERS).id == "mann"
    assert boe.needs_pdf(page)
    assert page.main_pdf_url.endswith("catherine-l-mann-jackson-hole-discussion-paper.pdf")


def test_speaker_box_linking_to_mpc_page_falls_back_to_name():
    items = boe.parse_feed(fixture("boe_speeches_feed.xml"))
    item = next(i for i in items if "Running on empty" in i.title)
    page = boe.parse_speech_page(fixture("boe_speech_dhingra_mpc_link.html"))
    assert boe.attribute_speech(item, page, MEMBERS).id == "dhingra"


def test_non_member_with_member_surname_is_dropped():
    items = boe.parse_feed(fixture("boe_speeches_feed.xml"))
    item = next(i for i in items if "role of research" in i.title)
    page = boe.parse_speech_page(fixture("boe_speech_david_bailey.html"))
    assert boe.attribute_speech(item, page, MEMBERS) is None


def test_source_type_hint():
    assert boe.source_type_hint("Slides from Huw Pill's fireside chat", "") == "comment"
    assert boe.source_type_hint("The outlook for inflation", "") == "speech"
