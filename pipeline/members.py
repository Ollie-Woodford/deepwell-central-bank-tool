"""
Match speakers in feeds and documents to members in config/members.json.

Matching uses full names only. Surname-only variants ("Bailey", "Taylor") are
kept in members.json for reading prose, but in feeds they collide with other
Bank staff (David Bailey of the PRA shares Andrew Bailey's surname), so they
are never used to attribute a document.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
MEMBERS_FILE = ROOT / "config" / "members.json"

# Honorifics stripped before comparing names.
_TITLES = re.compile(r"^(?:professor|prof|dr|sir|dame|mr|ms|mrs)\.?\s+", re.I)


def normalise_name(name: str) -> str:
    """Lower case, no accents, no honorifics, single spaces, no full stops."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace(".", " ").replace(" ", " ")
    s = re.sub(r"\s+", " ", s).strip().lower()
    while True:
        stripped = _TITLES.sub("", s)
        if stripped == s:
            return s
        s = stripped


@dataclass(frozen=True)
class Member:
    id: str
    bank: str
    name: str
    role: str
    full_names: frozenset   # normalised variants with at least two words
    bio_slug: Optional[str] # e.g. "catherine-mann" from the BoE biography URL
    surname_ja: Optional[str] = None  # BoJ: how Japanese documents name the member
    former: bool = False              # left the committee; kept so their votes still parse


def _bio_slug(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    m = re.search(r"/about/people/([^/]+)/", url)
    return m.group(1) if m else None


def load_members(path: Path = MEMBERS_FILE, bank: Optional[str] = None,
                 include_former: bool = False) -> list[Member]:
    """Current members; with include_former, also those listed for backfill."""
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = [(m, False) for m in data["members"]]
    if include_former:
        rows += [(m, True) for m in data.get("former_members_for_backfill", []) if "id" in m]
    out = []
    for m, former in rows:
        if bank and m["bank"] != bank:
            continue
        names = {normalise_name(v) for v in m["name_variants"] + [m["name"]]}
        out.append(Member(
            id=m["id"], bank=m["bank"], name=m["name"], role=m["role"],
            full_names=frozenset(n for n in names if " " in n),
            bio_slug=_bio_slug(m.get("bio")),
            surname_ja=m.get("surname_ja"),
            former=former,
        ))
    return out


def match_name(name: str, members: list[Member]) -> Optional[Member]:
    """The member whose full name matches exactly, or None."""
    n = normalise_name(name)
    for m in members:
        if n in m.full_names:
            return m
    return None


def match_bio_url(url: str, members: list[Member]) -> Optional[Member]:
    slug = _bio_slug(url)
    if not slug:
        return None
    for m in members:
        if m.bio_slug == slug:
            return m
    return None


def find_name_in_text(text: str, members: list[Member]) -> Optional[Member]:
    """The single member whose full name appears in text, or None if zero or several do."""
    t = " " + normalise_name(text) + " "
    hits = {m.id: m for m in members for n in m.full_names if f" {n} " in t}
    return next(iter(hits.values())) if len(hits) == 1 else None
