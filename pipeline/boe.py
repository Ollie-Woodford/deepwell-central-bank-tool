"""
Bank of England: speeches feed, speech pages and MPC minutes.

Parsing is kept separate from fetching so it can be tested against saved pages
(pipeline/tests/fixtures).

Speech pages: the full text is usually in the HTML. When the HTML body is only
a link (a "Read the speech" button), the text is in the linked PDF. Most other
PDF links on a page are footnote references and are ignored.

Minutes: from 2026, "MPC members' views on Bank Rate" groups members under
headings such as "Votes to increase Bank Rate to 4%", each followed by the
member's name and written statement. That one section gives each member's
vote, the rate they voted for, and their statement.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime, time
from email.utils import parsedate_to_datetime
from typing import Optional
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from .members import Member, find_name_in_text, match_bio_url, match_name

BASE = "https://www.bankofengland.co.uk"
FEED_URL = f"{BASE}/rss/speeches"
LONDON = ZoneInfo("Europe/London")
MINUTES_RELEASE = time(12, 0)  # minutes are published at noon London time

# Below this many characters the HTML body is taken to be a link to the PDF.
MIN_HTML_TEXT = 1500

MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]
_DATE_IN_TEXT = re.compile(
    r"(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(MONTHS) + r")\s+(\d{4})", re.I)


def _parse_text_date(text: str) -> Optional[date]:
    """The last 'day month year' date in a piece of text."""
    hits = _DATE_IN_TEXT.findall(text or "")
    if not hits:
        return None
    d, m, y = hits[-1]
    return date(int(y), MONTHS.index(m.lower()) + 1, int(d))


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace(" ", " ")).strip()


# ---------------------------------------------------------------- speeches

@dataclass
class FeedItem:
    guid: str
    url: str
    title: str
    description: str
    published: datetime  # timezone aware


def parse_feed(xml_text: str) -> list[FeedItem]:
    root = ET.fromstring(xml_text)
    items = []
    for it in root.iter("item"):
        items.append(FeedItem(
            guid=it.findtext("guid", "").strip(),
            url=it.findtext("link", "").strip(),
            title=_clean(it.findtext("title", "")),
            description=_clean(it.findtext("description", "")),
            published=parsedate_to_datetime(it.findtext("pubDate")),
        ))
    return items


@dataclass
class SpeechPage:
    title: str
    description: str
    speaker_names: list[str]
    speaker_bio_urls: list[str]
    html_text: str
    main_pdf_url: Optional[str]


def parse_speech_page(html: str) -> SpeechPage:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup
    h1 = main.find("h1")
    desc = main.find(class_="page-description")

    names, bios = [], []
    for a in main.select("a.med-block-cta"):
        h3 = a.find("h3")
        if h3:
            names.append(_clean(h3.get_text()))
            bios.append(a.get("href", ""))

    # page-content divs nest inside each other; the outermost holds everything.
    blocks = [b for b in main.select("div.content-block div.page-content")
              if b.find_parent(class_="page-content") is None]
    # Footnotes and endnotes are references, not policy content.
    for li in main.select("li[id^=footnote], li[id^=endnote]"):
        if li.parent is not None and li.parent.name == "ol":
            li.parent.decompose()
    paras = []
    main_pdf = None
    for b in blocks:
        for el in b.find_all(["p", "h2", "h3", "h4", "li", "blockquote"]):
            if el.find_parent(["li", "blockquote"]) and el.name not in ("li", "blockquote"):
                continue  # counted with its parent
            t = _clean(el.get_text(" "))
            if t:
                paras.append(t)
        if main_pdf is None:
            btn = b.select_one("a.btn-pubs[href$='.pdf'], a.btn-pubs[href*='.pdf?']")
            if btn:
                main_pdf = btn["href"]
    if main_pdf and main_pdf.startswith("/"):
        main_pdf = BASE + main_pdf

    return SpeechPage(
        title=_clean(h1.get_text()) if h1 else "",
        description=_clean(desc.get_text(" ")) if desc else "",
        speaker_names=names,
        speaker_bio_urls=bios,
        html_text="\n\n".join(paras),
        main_pdf_url=main_pdf,
    )


def attribute_speech(item: FeedItem, page: SpeechPage, members: list[Member]) -> Optional[Member]:
    """Biography link first, then the speaker box name, then a full name in the title."""
    for url in page.speaker_bio_urls:
        m = match_bio_url(url, members)
        if m:
            return m
    for name in page.speaker_names:
        m = match_name(name, members)
        if m:
            return m
    if page.speaker_names:
        return None  # a named speaker who is not a member
    return find_name_in_text(item.title, members)


def source_type_hint(title: str, description: str) -> str:
    """First guess at the source type; the scorer confirms it (WEIGHTING.md section 4)."""
    t = f"{title} {description}".lower()
    if "fireside" in t or "panel" in t:
        return "comment"
    return "speech"


def speech_doc_id(item: FeedItem) -> str:
    slug = item.url.rstrip("/").rsplit("/", 1)[-1]
    return f"boe-speech-{item.published.date().isoformat()}-{slug}"[:120]


def needs_pdf(page: SpeechPage) -> bool:
    return len(page.html_text) < MIN_HTML_TEXT and page.main_pdf_url is not None


def speech_record(item: FeedItem, page: SpeechPage, member: Member,
                  text: str, text_source: str, collected_at: str) -> dict:
    from .store import iso_utc

    delivered = _parse_text_date(page.description or item.description)
    return {
        "id": speech_doc_id(item),
        "bank": "BoE",
        "kind": "speech",
        "member_id": member.id,
        "speaker_name": page.speaker_names[0] if page.speaker_names else member.name,
        "title": page.title or item.title,
        "description": page.description or item.description,
        "url": item.url,
        "text_url": page.main_pdf_url if text_source == "pdf" else item.url,
        "published": iso_utc(item.published),
        "delivered_date": delivered.isoformat() if delivered else None,
        "source_type_hint": source_type_hint(item.title, page.description),
        "language": "en",
        "text_source": text_source,
        "text": text,
        "collected_at": collected_at,
    }


# ---------------------------------------------------------------- minutes

def minutes_url(announcement: date) -> str:
    month = MONTHS[announcement.month - 1]
    return f"{BASE}/monetary-policy-summary-and-minutes/{announcement.year}/{month}-{announcement.year}"


@dataclass
class MemberVote:
    name: str
    member: Optional[Member]
    voted_rate: float
    statement: str


@dataclass
class Minutes:
    meeting_end: Optional[date]
    previous_rate: float
    decision_rate: float
    votes: list[MemberVote] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)


_SUMMARY = re.compile(
    r"voted (?:by a majority of (\d+)\D(\d+)|unanimously) to (maintain|increase|reduce) Bank Rate "
    r"(?:at|(?:by ([\d.]+) percentage points?,? )?to) ([\d.]+)%", re.I)
_GROUP = re.compile(r"^Votes? to (maintain|increase|reduce) Bank Rate\b.*?([\d.]+)%\s*$", re.I)
_MEETING_END = re.compile(r"meeting ending on (\d{1,2} \w+ \d{4})", re.I)


def parse_minutes(html: str, members: list[Member]) -> Minutes:
    soup = BeautifulSoup(html, "html.parser")
    text = _clean(soup.get_text(" "))

    m = _SUMMARY.search(text)
    if not m:
        raise ValueError("decision sentence not found in minutes")
    split = (int(m.group(1)), int(m.group(2))) if m.group(1) else None
    kind, delta, rate = m.group(3).lower(), m.group(4), float(m.group(5))
    if kind == "maintain":
        previous = rate
    else:
        if delta is None:
            raise ValueError(f"size of the move not found: {m.group(0)!r}")
        previous = rate - float(delta) if kind == "increase" else rate + float(delta)
    previous = round(previous, 4)

    end = _MEETING_END.search(text)
    minutes = Minutes(
        meeting_end=_parse_text_date(end.group(1)) if end else None,
        previous_rate=previous, decision_rate=rate,
    )

    heading = next((h for h in soup.find_all(["h2", "h3"])
                    if "views" in h.get_text().lower() and "member" in h.get_text().lower()), None)
    if heading is None:
        raise ValueError("'MPC members' views' section not found")

    group_rate = None
    current = None
    for el in heading.find_all_next():
        if el.name in ("h2", "h3"):
            break
        if el.name != "p":
            continue
        strong = el.find("strong")
        label = _clean(strong.get_text()) if strong else ""
        whole = _clean(el.get_text(" "))
        g = _GROUP.match(label) if label and label == whole else None
        # The colon after a member's name is sometimes inside the bold tag
        # ("<strong>Andrew Bailey:</strong>") and sometimes outside it.
        colon_after = whole.startswith(label) and whole[len(label):].lstrip().startswith(":")
        named = bool(label) and len(label) < 60 and (label.endswith(":") or colon_after)
        if g:
            group_rate = float(g.group(2))
            current = None
        elif named and group_rate is not None:
            name = label.rstrip(":").strip()
            member = match_name(name, members)
            if member is None:
                minutes.unmatched.append(name)
            body = whole[len(label):].lstrip().removeprefix(":")
            current = MemberVote(name, member, group_rate, _clean(body))
            minutes.votes.append(current)
        elif current is not None and whole:
            current.statement += "\n\n" + whole  # statement runs over several paragraphs

    if not minutes.votes:
        raise ValueError("no member votes found in minutes")
    if split and len(minutes.votes) != sum(split):
        raise ValueError(f"found {len(minutes.votes)} member votes, expected {sum(split)} "
                         f"from the {split[0]}-{split[1]} split")
    return minutes


def minutes_release_time(announcement: date) -> datetime:
    return datetime.combine(announcement, MINUTES_RELEASE, tzinfo=LONDON)
