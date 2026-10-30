"""
Federal Reserve: FOMC statements (decision and votes), Chair's press
conference transcripts, and speeches by the 12 FOMC voters.

Statements give the target range; every rate here is the upper bound of the
range (3-3/4 to 4 percent is stored as 4.0), so a 25bp move is 0.25 as at
the other banks.

Two statement formats:
  - to April 2026: "Voting for the monetary policy action were ...; Voting
    against this action were X, who preferred to lower ...". Every voter named.
  - from June 2026 (Chair Warsh): "approved ... by a 10-2 vote" and only the
    dissenters named. The majority is every 2026 voter in config/members.json
    in office on the day, minus the dissenters (`voters_on`).

Speeches:
  - Board governors: federalreserve.gov/json/ne-speeches.json (every speech,
    newest first), text from the speech page.
  - New York (Williams), Cleveland (Hammack), Dallas (Logan), Minneapolis
    (Kashkari), Philadelphia (Paulson): each bank's own speech list.
"""

from __future__ import annotations

import html as htmllib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time
from fractions import Fraction
from typing import Optional
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from .members import MEMBERS_FILE, Member, match_name, normalise_name

BOARD = "https://www.federalreserve.gov"
EASTERN = ZoneInfo("America/New_York")
STATEMENT_TIME = time(14, 0)
PRESS_TIME = time(14, 30)
SPEECH_TIME = time(12, 0)   # used when a page gives no time

CALENDAR_URL = BOARD + "/monetarypolicy/fomccalendars.htm"
BOARD_SPEECHES_JSON = BOARD + "/json/ne-speeches.json"
NY_INDEX = "https://www.newyorkfed.org/newsevents/speeches/index"
CLEVELAND_INDEX = "https://www.clevelandfed.org/collections/speeches"
DALLAS_INDEX = "https://www.dallasfed.org/news/speeches/logan"
MINNEAPOLIS_INDEX = "https://www.minneapolisfed.org/people/neel-kashkari"
PHILADELPHIA_INDEX = "https://www.philadelphiafed.org/the-economy/speeches-anna-paulson"


def squash(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace(" ", " ")).strip()


# ---------------------------------------------------------------- statements

def statement_urls(calendar_html: str) -> dict[date, str]:
    """Statement press releases linked from the FOMC calendar page, by date."""
    out = {}
    for y, m, d in re.findall(r"/newsevents/pressreleases/monetary(\d{4})(\d\d)(\d\d)a\.htm", calendar_html):
        out[date(int(y), int(m), int(d))] = f"{BOARD}/newsevents/pressreleases/monetary{y}{m}{d}a.htm"
    return out


_FRACTION = re.compile(r"(\d+)?[\s‑-]*(?:(\d)/(\d)|([¼½¾]))")
_VULGAR = {"¼": Fraction(1, 4), "½": Fraction(1, 2), "¾": Fraction(3, 4)}


def parse_number(s: str) -> float:
    """'3-1/2', '3‑1/2', '3¾', '4', '1/4' to a float."""
    s = s.strip()
    m = _FRACTION.fullmatch(s)
    if not m:
        return float(s)
    whole = int(m.group(1)) if m.group(1) else 0
    frac = _VULGAR[m.group(4)] if m.group(4) else Fraction(int(m.group(2)), int(m.group(3)))
    return float(whole + frac)


_NUM = r"\d+(?:[\s‑-]*\d/\d|[¼½¾])?|\d/\d|[¼½¾]"
_RANGE = re.compile(rf"target range for the federal funds rate (?:by (?P<by>{_NUM}) percentage point )?"
                    rf"(?:at|to) (?P<lo>{_NUM}) to (?P<hi>{_NUM}) percent")
_ACTION = re.compile(r"Committee decided to (?P<verb>maintain|raise|lower)")
_PREFERRED = re.compile(rf"preferred to (?P<verb>raise|lower) the target range for the federal funds rate "
                        rf"by (?P<by>{_NUM}) percentage point")
_HOLD_PREF = re.compile(r"(?:preferred to maintain|supported maintaining) the target range")
_GUIDANCE = re.compile(r"did not support (?:inclusion of )?(?:an? )?(?P<what>easing|tightening) bias")


@dataclass
class Dissent:
    names: list[str]
    voted_rate: Optional[float]   # None: backed the rate, dissented on guidance
    guidance: int = 0             # +1 against an easing bias, -1 against a tightening bias
    text: str = ""


@dataclass
class Statement:
    previous_rate: float
    decision_rate: float
    low: float
    voters_listed: list[str] = field(default_factory=list)  # majority names, old format only
    dissents: list[Dissent] = field(default_factory=list)
    tally: Optional[tuple[int, int]] = None


def _names(seg: str) -> list[str]:
    seg = re.sub(r",\s*(?:Chair|Vice Chair|Chairman)\b", "", seg)
    parts = re.split(r";|,\s*and\s+|\s+and\s+|,", seg)
    return [p.strip(" .") for p in parts if re.search(r"[A-Z][a-z]", p or "")]


def parse_statement(page_html: str) -> Statement:
    soup = BeautifulSoup(page_html, "html.parser")
    t = squash((soup.find(id="article") or soup).get_text(" "))
    r = _RANGE.search(t)
    a = _ACTION.search(t)
    if not r or not a:
        raise ValueError("no federal funds rate decision found")
    lo, hi = parse_number(r.group("lo")), parse_number(r.group("hi"))
    by = parse_number(r.group("by")) if r.group("by") else 0.0
    move = {"maintain": 0.0, "raise": by, "lower": -by}[a.group("verb")]
    st = Statement(previous_rate=hi - move, decision_rate=hi, low=lo)

    tally = re.search(r"by an? (\d+)\s*[–-]\s*(\d+) vote", t)
    if tally:
        st.tally = (int(tally.group(1)), int(tally.group(2)))
    fav = re.search(r"Voting for (?:the|this) monetary policy action were (.*?)\.\s+Voting against", t) \
        or re.search(r"Voting for (?:the|this) monetary policy action were (.*?)\.(?:\s|$)", t)
    if fav:
        st.voters_listed = _names(fav.group(1))
    against = re.search(r"Voting against (?:the|this) (?:monetary policy )?action (?:were|was) (.*?)(?:For media inquiries|"
                        r"Implementation Note|$)", t)
    if against:
        for clause in re.split(r";\s*and\s+|;\s+", against.group(1)):
            who = re.split(r",?\s+who\s+", clause, maxsplit=1)
            names = _names(who[0])
            why = who[1] if len(who) > 1 else ""
            p = _PREFERRED.search(clause)
            g = _GUIDANCE.search(clause)
            if p:
                step = parse_number(p.group("by"))
                rate = hi + (step if p.group("verb") == "raise" else -step)
                st.dissents.append(Dissent(names, rate, 0, why))
            elif g:
                st.dissents.append(Dissent(names, None, 1 if g.group("what") == "easing" else -1, why))
            elif _HOLD_PREF.search(clause):
                st.dissents.append(Dissent(names, st.previous_rate if move else hi, 0, why))
            else:
                raise ValueError(f"dissent not understood: {clause[:200]}")
    return st


def _member_rows(path=MEMBERS_FILE) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [m for m in data["members"] + data.get("former_members_for_backfill", [])
            if m.get("bank") == "Fed" and "id" in m]


def voters_on(d: date, path=MEMBERS_FILE) -> list[str]:
    """FOMC voters in office on `d`: Board members and the year's voting presidents."""
    out = []
    for m in _member_rows(path):
        if not (m.get("term_start", "0000") <= d.isoformat() <= m.get("term_end", "9999")):
            continue
        voter = m.get("fomc_voter")
        if m.get("seat") == "Board" or voter == "permanent" or voter == str(d.year):
            out.append(m["id"])
    return out


@dataclass
class MeetingVotes:
    rates: dict[str, float]
    guidance: dict[str, int]
    unmatched: list[str]


def meeting_votes(st: Statement, d: date, members: list[Member]) -> MeetingVotes:
    unmatched: list[str] = []

    def ids(names: list[str]) -> list[str]:
        got = []
        for n in names:
            m = match_name(n, members)
            if m is None:
                unmatched.append(n)
            else:
                got.append(m.id)
        return got

    rates: dict[str, float] = {}
    guidance: dict[str, int] = {}
    for dis in st.dissents:
        for mid in ids(dis.names):
            rates[mid] = dis.voted_rate if dis.voted_rate is not None else st.decision_rate
            if dis.guidance:
                guidance[mid] = dis.guidance
    majority = ids(st.voters_listed) if st.voters_listed else [m for m in voters_on(d) if m not in rates]
    for mid in majority:
        rates.setdefault(mid, st.decision_rate)
    if st.tally and sum(st.tally) != len(rates):
        unmatched.append(f"vote count {st.tally[0]}-{st.tally[1]} but {len(rates)} voters found")
    return MeetingVotes(rates, guidance, unmatched)


def statement_time(d: date) -> datetime:
    return datetime.combine(d, STATEMENT_TIME, tzinfo=EASTERN)


# ---------------------------------------------------------- press conferences

def press_pdf_url(d: date) -> str:
    return f"{BOARD}/mediacenter/files/FOMCpresconf{d:%Y%m%d}.pdf"


def press_page_url(d: date) -> str:
    return f"{BOARD}/monetarypolicy/fomcpresconf{d:%Y%m%d}.htm"


_SPEAKER = re.compile(r"^([A-Z][A-Z .'’-]{2,60})\.\s", re.M)
_RUNNING = re.compile(r"^(?:[A-Z][a-z]+ \d{1,2}, \d{4} .*Press Conference.*|Page \d+ of \d+|"
                      r"Transcript of .*Press Conference|[A-Z][a-z]+ \d{1,2}, \d{4})\s*$", re.M)


def chair_remarks(transcript: str) -> str:
    """The Chair's words only, in order; reporters' questions are dropped.
    Paragraph breaks become blank lines; line wraps inside a paragraph are joined."""
    body = _RUNNING.sub("", transcript)
    marks = list(_SPEAKER.finditer(body))
    keep = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        if m.group(1).startswith("CHAIR"):
            seg = body[m.end():end].strip()
            keep.append(re.sub(r"\s*\n\s*", " ", seg))
    return "\n\n".join(s for s in keep if s)


def chair_on(d: date) -> str:
    """Member id of the Chair on date d."""
    for m in _member_rows():
        if m.get("role") == "Chair" and m.get("term_start", "9999") <= d.isoformat():
            return m["id"]
        if m.get("chair_until") and d.isoformat() <= m["chair_until"]:
            return m["id"]
    raise ValueError(f"no Chair on {d}")


# ------------------------------------------------------------------ speeches

@dataclass
class SpeechItem:
    url: str
    title: str
    speaker: str
    when: datetime         # Eastern time
    location: str = ""
    pdf_url: Optional[str] = None


def _eastern(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=EASTERN)


def parse_board_speeches(raw_json: str) -> list[SpeechItem]:
    out = []
    for r in json.loads(raw_json.lstrip("﻿")):
        if not r.get("l") or not r.get("d"):
            continue
        d = r["d"].strip()
        when = datetime.strptime(d, "%m/%d/%Y %I:%M:%S %p" if " " in d else "%m/%d/%Y")
        out.append(SpeechItem(url=BOARD + r["l"], title=htmllib.unescape(r.get("t", "")).strip(),
                              speaker=htmllib.unescape(r.get("s", "")).strip(), when=_eastern(when),
                              location=htmllib.unescape(r.get("lo", "")).strip()))
    return out


def board_speech_text(page_html: str) -> str:
    """Speech body without footnote markers or the footnote list."""
    soup = BeautifulSoup(page_html, "html.parser")
    art = soup.find(id="article") or soup
    for a in art.find_all("a", href=re.compile(r"^#fn\d")):
        a.decompose()
    cols = art.find_all("div", recursive=False)
    body = max(cols, key=lambda c: len(c.find_all("p", recursive=False))) if cols else art
    paras = []
    for el in body.find_all(["p", "hr", "h4", "h5"], recursive=False):
        if el.name == "hr":
            break                       # footnotes follow the rule
        txt = squash(el.get_text(" "))
        if txt:
            paras.append(txt)
    return "\n\n".join(paras)


def parse_ny_index(page_html: str) -> list[SpeechItem]:
    """Williams's speeches from the New York Fed list (other officials are skipped)."""
    out, seen = [], set()
    for path, yy, mm, dd in re.findall(r'href="(/newsevents/speeches/\d{4}/wil(\d\d)(\d\d)(\d\d))"', page_html):
        if path in seen:
            continue
        seen.add(path)
        title = ""
        m = re.search(re.escape(path) + r'"[^>]*>(.*?)</a>', page_html, re.S)
        if m:
            title = re.sub(r"^Williams:\s*", "", squash(BeautifulSoup(m.group(1), "html.parser").get_text(" ")))
        when = datetime.combine(date(2000 + int(yy), int(mm), int(dd)), SPEECH_TIME, tzinfo=EASTERN)
        out.append(SpeechItem("https://www.newyorkfed.org" + path, title, "John C. Williams", when))
    return out


def parse_cleveland_index(page_html: str) -> list[SpeechItem]:
    """Cleveland embeds its list as JSON in the page."""
    raw = htmllib.unescape(page_html)
    out = []
    for m in re.finditer(r'\{"index":\d+,"url":"(/collections/speeches/[^"]+)".*?"title":"(.*?)",'
                         r'.*?"releaseDate":"([^"]+)".*?"authors":\[(.*?)\](.*?)"pdf_Url":"([^"]*)"', raw):
        path, title, released, authors, rest, pdf = m.groups()
        st = re.search(r'"speechTime":"([^"]+)"', rest)
        when = datetime.fromisoformat(st.group(1) if st else released)
        names = re.findall(r'"label":"([^"]+)"', authors)
        out.append(SpeechItem("https://www.clevelandfed.org" + path, title, ", ".join(names), when,
                              pdf_url=pdf or None))
    return out


def parse_dallas_index(page_html: str) -> list[SpeechItem]:
    soup = BeautifulSoup(page_html, "html.parser")
    out, seen = [], set()
    for a in soup.find_all("a", href=re.compile(r"/news/speeches/logan/\d{4}/lkl\d{6}")):
        href = a["href"]
        if href in seen:
            continue
        seen.add(href)
        yy, mm, dd = re.search(r"lkl(\d\d)(\d\d)(\d\d)", href).groups()
        when = datetime.combine(date(2000 + int(yy), int(mm), int(dd)), SPEECH_TIME, tzinfo=EASTERN)
        url = href if href.startswith("http") else "https://www.dallasfed.org" + href
        out.append(SpeechItem(url, squash(a.get_text(" ")), "Lorie K. Logan", when))
    return out


def parse_minneapolis_index(page_html: str) -> list[SpeechItem]:
    """Kashkari's speeches linked from his profile page; dates come from each page."""
    out, seen = [], set()
    for path in re.findall(r'href="(/speeches/\d{4}/[^"#?]+)"', page_html):
        if path not in seen:
            seen.add(path)
            out.append(SpeechItem("https://www.minneapolisfed.org" + path, "", "Neel Kashkari",
                                  datetime(int(path.split("/")[2]), 1, 1, tzinfo=EASTERN)))
    return out


def parse_philadelphia_index(page_html: str) -> list[SpeechItem]:
    out, seen = [], set()
    for path, yy, mm, dd in re.findall(r'href="(/the-economy/monetary-policy/(\d\d)(\d\d)(\d\d)-[^"#?]+)"', page_html):
        if path not in seen:
            seen.add(path)
            when = datetime.combine(date(2000 + int(yy), int(mm), int(dd)), SPEECH_TIME, tzinfo=EASTERN)
            out.append(SpeechItem("https://www.philadelphiafed.org" + path, "", "Anna Paulson", when))
    return out


_DROP = re.compile(r"^(?:Return to text|Share|Print|Download|Related|Watch|Listen)\b", re.I)


def reserve_bank_text(page_html: str) -> tuple[str, str, Optional[datetime]]:
    """(title, body, published) from a Reserve Bank speech page: the element
    holding the most paragraph text, footnotes and boilerplate removed."""
    soup = BeautifulSoup(page_html, "html.parser")
    for t in soup(["script", "style", "nav", "header", "footer", "aside", "sup"]):
        t.decompose()
    for t in soup.select('[class*="footnote"], [id*="footnote"], [class*="related"]'):
        t.decompose()
    title = ""
    og = soup.find("meta", property="og:title")
    h1 = soup.find("h1")
    if h1 and squash(h1.get_text(" ")):
        title = squash(h1.get_text(" "))
    elif og:
        title = og.get("content", "").strip()
    published = None
    for name in ("ess:publishdatetime", "citation_date", "article:published_time"):
        meta = soup.find("meta", attrs={"name": name}) or soup.find("meta", property=name)
        if meta and meta.get("content"):
            v = meta["content"].replace("Z", "+00:00")
            published = _eastern(datetime.fromisoformat(v if "T" in v else v + "T12:00:00"))
            break
    weight: dict = {}
    for p in soup.find_all("p"):
        weight[id(p.parent)] = (p.parent, weight.get(id(p.parent), (None, 0))[1] + len(p.get_text()))
    if not weight:
        return title, "", published
    box = max(weight.values(), key=lambda x: x[1])[0]
    paras = []
    for p in box.find_all(["p", "h2", "h3", "li"]):
        txt = squash(p.get_text(" "))
        if txt and not _DROP.match(txt):
            paras.append(txt)
    return title, "\n\n".join(paras), published


def speech_doc_id(member_id: str, d: date, title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", normalise_name(title))[:60].strip("-") or "remarks"
    return f"fed-speech-{d.isoformat()}-{member_id}-{slug}"
