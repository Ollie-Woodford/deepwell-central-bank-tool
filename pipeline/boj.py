"""
Bank of Japan: policy decisions, speeches and press conferences.

Decisions: the Statement on Monetary Policy (a hold) or "Change in the
Guideline for Money Market Operations" (a move) names how each member voted:
"Voting for the action: ...", "Voting against the action: ...", "Absent: ...",
then each dissenter's reasoning and any proposal ("He proposed ... remain at
around 1.25 percent"). PDF text splits words with stray spaces ("V oting",
"TAKA TA"), so decisions are parsed from text with all whitespace removed.

Speeches: the English index (koen_YYYY) lists date, speaker and title; the
speech page links the full text as a PDF.

Press conferences: published in Japanese only (kaiken_YYYY), as PDFs, a few
days after the event. Each opens with the exact date and time. Stored text is
NFKC-normalised (full-width digits become ASCII) with the stray spaces and
line breaks inside Japanese sentences removed.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from .members import Member

BASE = "https://www.boj.or.jp"
TOKYO = ZoneInfo("Asia/Tokyo")
SPEECH_TIME = time(10, 30)   # speech times are not published; mid-morning Tokyo assumed
DECISION_TIME = time(12, 0)  # used only when the meeting hours cannot be read

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def speech_index_url(year: int) -> str:
    return f"{BASE}/en/about/press/koen_{year}/index.htm"


def statement_index_url(year: int) -> str:
    return f"{BASE}/en/mopo/mpmdeci/state_{year}/index.htm"


def press_index_url(year: int) -> str:
    return f"{BASE}/about/press/kaiken_{year}/index.htm"


def _abs(url: str) -> str:
    return BASE + url if url.startswith("/") else url


def parse_en_date(s: str) -> Optional[date]:
    """'Sept. 18, 2026', 'June 3, 2026', 'Oct. 15, 2026'."""
    m = re.match(r"\s*([A-Za-z]+)\.?\s+(\d{1,2}),\s*(\d{4})", s)
    if not m or m.group(1)[:3].lower() not in MONTHS:
        return None
    return date(int(m.group(3)), MONTHS[m.group(1)[:3].lower()], int(m.group(2)))


def squash(s: str) -> str:
    return re.sub(r"\s+", "", s)


def _key(name: str) -> str:
    return squash(unicodedata.normalize("NFKC", name)).lower()


def name_keys(m: Member) -> set[str]:
    """'TAKATA Hajime' and 'Takata Hajime' both become 'takatahajime'."""
    return {_key(n) for n in m.full_names}


def members_in(segment: str, members: list[Member]) -> list[Member]:
    seg = segment.lower()
    return [m for m in members if any(k in seg for k in name_keys(m))]


# ---------------------------------------------------------------- decisions

@dataclass
class IndexItem:
    date: date
    title: str
    url: str


def parse_statement_index(html: str) -> list[IndexItem]:
    """The policy decision of each meeting: a Statement or a Change in the Guideline."""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        a = tr.find("a", href=True)
        if len(tds) < 2 or a is None:
            continue
        d = parse_en_date(tds[0].get_text(" "))
        title = re.sub(r"\s+", " ", a.get_text(" ")).strip()
        if d is None or title.startswith("(Reference)"):
            continue
        if title.startswith("Statement on Monetary Policy") or title.startswith("Change in the Guideline for Money Market Operations"):
            out.append(IndexItem(d, title, _abs(a["href"])))
    return out


@dataclass
class Decision:
    rate: float
    voting_for: list[Member]
    voting_against: list[Member]
    absent: list[Member]
    proposals: dict[str, float]          # member id -> rate proposed
    split: Optional[tuple[int, int]]
    ended: Optional[time]                # meeting end time, Tokyo
    unmatched: list[str] = field(default_factory=list)


_DECIDED = re.compile(
    r"decided,bya(?:n)?(?:(\d+)-(\d+)majority|unanimous)vote,tosetthefollowingguidelineformoneymarketoperations"
    r".*?remainataround([\d.]+)percent")
_PROPOSAL = re.compile(r"(?:He|She|They)proposedthattheBank.*?remainataround([\d.]+)percent")


def _list_after(sq: str, label: str) -> Optional[str]:
    i = sq.find(label)
    if i < 0:
        return None
    j = sq.find(".", i + len(label))
    return sq[i + len(label): j if j > 0 else None]


def _names_in_list(seg: str) -> list[str]:
    parts = re.split(r",(?:and)?|(?<=[a-z])and(?=[A-Z]{2})", seg)
    return [p for p in (x.strip() for x in parts) if p]


def parse_decision(text: str, members: list[Member]) -> Decision:
    sq = squash(text)
    m = _DECIDED.search(sq)
    if not m:
        raise ValueError("guideline decision sentence not found")
    split = (int(m.group(1)), int(m.group(2))) if m.group(1) else None
    rate = float(m.group(3).rstrip("."))

    unmatched: list[str] = []

    def resolve(label: str) -> list[Member]:
        seg = _list_after(sq, label)
        if seg is None:
            return []
        found = members_in(seg, members)
        for name in _names_in_list(seg):
            if not members_in(name, members):
                unmatched.append(name)
        return found

    voting_for = resolve("Votingfortheaction:")
    voting_against = resolve("Votingagainsttheaction:")
    absent = resolve("Absent:")
    if split is None:
        # Unanimous: everyone present voted for the guideline. Any "Voting for/against"
        # lists in the document belong to other decisions (a bond purchase plan, say).
        seg = sq[sq.find("PolicyBoardmemberspresent:"):]
        seg = seg[:seg.find("[Otherspresent]")] if "[Otherspresent]" in seg else seg[:400]
        present = members_in(seg, members)
        voting_for = [m for m in present if m not in absent] or voting_for
        voting_against = []

    # Each proposal belongs to the dissenter named last before it ("They" covers all).
    proposals: dict[str, float] = {}
    for p in _PROPOSAL.finditer(sq):
        r = float(p.group(1).rstrip("."))
        if p.group(0).startswith("They"):
            for d in voting_against:
                proposals.setdefault(d.id, r)
            continue
        before = sq[:p.start()]
        last = max(voting_against, key=lambda d: max(before.lower().rfind(k) for k in name_keys(d)), default=None)
        if last is not None:
            proposals[last.id] = r

    ended = None
    hours = sq[sq.find("Meetinghours:"):][:200] if "Meetinghours:" in sq else ""
    times = re.findall(r"(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})", hours)
    if times:
        ended = time(int(times[-1][2]), int(times[-1][3]))

    dec = Decision(rate, voting_for, voting_against, absent, proposals, split, ended, unmatched)
    if split and len(voting_for) + len(voting_against) != sum(split):
        raise ValueError(f"found {len(voting_for)} for and {len(voting_against)} against, "
                         f"expected the {split[0]}-{split[1]} split")
    return dec


def voted_rates(dec: Decision, previous: float) -> tuple[dict[str, float], list[str]]:
    """Each voter's rate. A dissenter with no proposal voted against the move, so
    for the previous rate; at a hold with no proposal their rate is unknown."""
    rates = {m.id: dec.rate for m in dec.voting_for}
    unknown = []
    for m in dec.voting_against:
        if m.id in dec.proposals:
            rates[m.id] = dec.proposals[m.id]
        elif abs(dec.rate - previous) > 1e-9:
            rates[m.id] = previous
        else:
            unknown.append(m.id)
    return rates, unknown


def decision_time(d: date, dec: Decision) -> datetime:
    return datetime.combine(d, dec.ended or DECISION_TIME, tzinfo=TOKYO)


# ---------------------------------------------------------------- speeches

@dataclass
class SpeechItem:
    date: date
    speaker: str
    title: str
    url: str


def parse_speech_index(html: str) -> list[SpeechItem]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        a = tr.find("a", href=True)
        if len(tds) < 3 or a is None or "/koen_" not in a["href"]:
            continue
        d = parse_en_date(tds[0].get_text(" "))
        if d is None:
            continue
        out.append(SpeechItem(d, re.sub(r"\s+", " ", tds[1].get_text(" ")).strip(),
                              re.sub(r"\s+", " ", tds[2].get_text(" ")).strip(), _abs(a["href"])))
    return out


def attribute_speaker(speaker: str, members: list[Member]) -> Optional[Member]:
    """'KOEDA Junko, Member of the Policy Board' -> koeda."""
    name = speaker.split(",")[0]
    key = _key(name)
    hits = [m for m in members if key in name_keys(m)]
    return hits[0] if len(hits) == 1 else None


def speech_pdf_url(html: str) -> Optional[str]:
    m = re.search(r'href="([^"]*/data/ko[^"]*\.pdf)"', html)
    return _abs(m.group(1)) if m else None


def clean_en_pdf_text(text: str) -> str:
    """Join wrapped lines, undo end-of-line hyphenation, drop bare page numbers."""
    lines = [ln.rstrip() for ln in text.splitlines()]
    lines = [ln for ln in lines if not re.fullmatch(r"\s*\d{1,3}\s*", ln)]
    t = "\n".join(lines)
    t = re.sub(r"-\n(?=[a-z])", "", t)
    t = re.sub(r"\n{2,}", " ", t)   # keep paragraph breaks
    t = re.sub(r"\s*\n\s*", " ", t)
    t = re.sub(r"[ \t]+", " ", t)
    return t.replace(" ", "\n\n").strip()


def speech_doc_id(item: SpeechItem) -> str:
    code = item.url.rstrip("/").rsplit("/", 1)[-1].split(".")[0]
    return f"boj-speech-{item.date.isoformat()}-{code}"


def speech_time(d: date) -> datetime:
    return datetime.combine(d, SPEECH_TIME, tzinfo=TOKYO)


# ---------------------------------------------------------------- press conferences

@dataclass
class PressItem:
    title: str
    member: Optional[Member]
    month: int
    day: int
    url: str


_PRESS = re.compile(r"^(?P<who>.*?)記者会見（(?:(?P<proxy>[^・（）]+?)副総裁代理・)?(?P<m>\d{1,2})月(?P<d>\d{1,2})日）")


def match_surname(text: str, members: list[Member]) -> Optional[Member]:
    hits = [m for m in members if m.surname_ja and text.startswith(m.surname_ja)]
    return max(hits, key=lambda m: len(m.surname_ja)) if hits else None


def parse_press_index(html: str, members: list[Member]) -> list[PressItem]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.find_all("a", href=True):
        if "/kaiken_" not in a["href"] or not re.search(r"kk\d{6}\w?\.(pdf|htm)$", a["href"]):
            continue
        title = re.sub(r"\[PDF.*$", "", a.get_text(" ").replace("\xa0", " ")).strip()
        m = _PRESS.match(unicodedata.normalize("NFKC", title).replace("(", "（").replace(")", "）"))
        if not m:
            continue
        who, proxy = m.group("who"), m.group("proxy")
        if proxy:
            member = match_surname(proxy, members)
        elif who.startswith("総裁"):
            member = next((x for x in members if x.id == "ueda"), None)
        else:
            member = match_surname(who, members)
        out.append(PressItem(title, member, int(m.group("m")), int(m.group("d")), _abs(a["href"])))
    return out


_JA = r"[　-ヿ一-鿿＀-￯]"


def clean_ja_text(text: str) -> str:
    t = unicodedata.normalize("NFKC", text)
    lines = [ln for ln in t.splitlines() if not re.fullmatch(r"\s*\d{1,3}\s*", ln)]
    t = "\n".join(lines)
    t = re.sub(rf"(?<={_JA})\s+|\s+(?={_JA})", "", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\s*(\((?:問|答)\))\s*", r"\n\n\1 ", t)
    return t.strip()


_HEADER = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日\(.\)(午前|午後)(\d{1,2})時(?:(\d{1,2})分)?")


def press_datetime(clean_text: str) -> Optional[datetime]:
    m = _HEADER.search(clean_text[:400])
    if not m:
        return None
    hour = int(m.group(5)) % 12 + (12 if m.group(4) == "午後" else 0)
    return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), hour, int(m.group(6) or 0), tzinfo=TOKYO)


def press_doc_id(item: PressItem, d: date) -> str:
    code = item.url.rsplit("/", 1)[-1].split(".")[0]
    return f"boj-press-{d.isoformat()}-{item.member.id}-{code}"


def html_main_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find(id="contents") or soup.find("main") or soup
    for s in main.find_all(["script", "style", "nav"]):
        s.decompose()
    return main.get_text("\n")
