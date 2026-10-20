"""
Check every source, save new documents to data/raw/, score votes by rule into
data/scores/, and record what has been seen in data/state.json.

    python -m pipeline.collect                 # new items from the last 92 days
    python -m pipeline.collect --since 2026-01-01
    python -m pipeline.collect --bank BoJ

Items that fail to fetch or parse are reported and left unseen, so the next
run tries them again.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import date, timedelta

import requests

from . import boe, boj, http
from .members import load_members
from .store import ROOT, State, append_scores, iso_utc, load_decisions, save_decision, utc_now_iso, write_raw
from .votes import VOTE_RULE_VERSION, Vote, score_meeting, split_label

CALENDAR_FILE = ROOT / "config" / "calendar.json"
DEFAULT_LOOKBACK_DAYS = 92


def collect_boe_speeches(state: State, since: date, log: list) -> None:
    members = load_members(bank="BoE")
    items = boe.parse_feed(http.get_text(boe.FEED_URL))
    for item in items:
        if item.published.date() < since or state.seen(item.url):
            continue
        try:
            page = boe.parse_speech_page(http.get_text(item.url))
            member = boe.attribute_speech(item, page, members)
            if member is None:
                who = ", ".join(page.speaker_names) or "no speaker named"
                state.mark(item.url, note=f"not an MPC member: {who}")
                continue
            if boe.needs_pdf(page):
                text, source = http.pdf_text(page.main_pdf_url), "pdf"
            else:
                text, source = page.html_text, "html"
            doc = boe.speech_record(item, page, member, text, source, utc_now_iso())
            write_raw(doc)
            state.mark(item.url, [doc["id"]])
            log.append(f"speech    {doc['published'][:10]}  {member.id:<12} {doc['title']}")
        except Exception as e:  # keep going; this item is retried next run
            log.append(f"ERROR     {item.url}: {e}")
            traceback.print_exc(file=sys.stderr)


def vote_records(bank: str, meeting: date, url: str, previous: float, decision: float,
                 rates: dict[str, float], ts: str, rate_name: str) -> list[dict]:
    """Votes scored by rule (pipeline/votes.py), as records for data/scores."""
    votes = [Vote(mid, r) for mid, r in rates.items()]
    label = split_label(previous, decision, votes)
    out = []
    for sv in score_meeting(previous, decision, votes):
        out.append({
            "id": f"{bank.lower()}-{meeting.isoformat()}-vote-{sv.member_id}",
            "member_id": sv.member_id,
            "bank": bank,
            "timestamp": ts,
            "source_type": sv.source_type,
            "document_url": url,
            "passage": f"Voted for {rate_name} at {sv.voted_rate:g}%; decision {decision:g}% ({label}).",
            "language": "en",
            "context": {"policy_rate": previous, "last_decision": label},
            "vote": {"previous_rate": previous, "decision_rate": decision, "voted_rate": sv.voted_rate},
            "score": sv.score,
            "confidence": 1.0,
            "flag": None,
            "rationale": sv.rationale,
            "rubric_version": VOTE_RULE_VERSION,
            "passage_weight_share": 1.0,
        })
    return out


def boe_vote_records(announcement: date, url: str, minutes: boe.Minutes) -> list[dict]:
    rates = {v.member.id: v.voted_rate for v in minutes.votes if v.member}
    return vote_records("BoE", announcement, url, minutes.previous_rate, minutes.decision_rate, rates,
                        iso_utc(boe.minutes_release_time(announcement)), "Bank Rate")


def boe_statement_docs(announcement: date, url: str, minutes: boe.Minutes) -> list[dict]:
    votes = [Vote(v.member.id, v.voted_rate) for v in minutes.votes if v.member]
    label = split_label(minutes.previous_rate, minutes.decision_rate, votes)
    published = iso_utc(boe.minutes_release_time(announcement))
    month = announcement.strftime("%B %Y")
    docs = []
    for v in minutes.votes:
        if v.member is None or not v.statement:
            continue
        docs.append({
            "id": f"boe-minutes-{announcement.isoformat()}-{v.member.id}",
            "bank": "BoE",
            "kind": "minutes_statement",
            "member_id": v.member.id,
            "speaker_name": v.name,
            "title": f"MPC minutes {month}: written statement",
            "description": f"Meeting ending {minutes.meeting_end}; decision {label}",
            "url": url,
            "text_url": url,
            "published": published,
            "delivered_date": announcement.isoformat(),
            "source_type_hint": "minutes_statement",
            "language": "en",
            "text_source": "html",
            "text": v.statement,
            "vote": {"previous_rate": minutes.previous_rate,
                     "decision_rate": minutes.decision_rate,
                     "voted_rate": v.voted_rate},
            "collected_at": utc_now_iso(),
        })
    return docs


def collect_boe_minutes(state: State, since: date, today: date, log: list) -> None:
    members = load_members(bank="BoE")
    calendar = json.loads(CALENDAR_FILE.read_text())
    for d in calendar["BoE"]["announcements"]:
        announcement = date.fromisoformat(d)
        url = boe.minutes_url(announcement)
        if not since <= announcement <= today or state.seen(url):
            continue
        try:
            minutes = boe.parse_minutes(http.get_text(url), members)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                log.append(f"waiting   minutes for {d} not published yet")
                continue
            log.append(f"ERROR     {url}: {e}")
            continue
        except Exception as e:
            log.append(f"ERROR     {url}: {e}")
            traceback.print_exc(file=sys.stderr)
            continue
        if minutes.unmatched:
            # A name we can't attribute means members.json is out of date. Stop
            # rather than record a meeting with a member missing.
            log.append(f"ERROR     {url}: unknown members {minutes.unmatched}; update config/members.json")
            continue
        save_decision({
            "bank": "BoE", "date": d, "announced": iso_utc(boe.minutes_release_time(announcement)),
            "url": url, "previous_rate": minutes.previous_rate, "decision_rate": minutes.decision_rate,
            "label": split_label(minutes.previous_rate, minutes.decision_rate,
                                 [Vote(v.member.id, v.voted_rate) for v in minutes.votes]),
            "votes": {v.member.id: v.voted_rate for v in minutes.votes},
        })
        docs = boe_statement_docs(announcement, url, minutes)
        for doc in docs:
            write_raw(doc)
        n_votes = append_scores(boe_vote_records(announcement, url, minutes))
        state.mark(url, [doc["id"] for doc in docs])
        label = split_label(minutes.previous_rate, minutes.decision_rate,
                            [Vote(v.member.id, v.voted_rate) for v in minutes.votes])
        log.append(f"minutes   {d}  {label:<16} {len(docs)} statements, {n_votes} votes recorded")


def _get_or_none(url: str):
    """Page text, or None for a page that does not exist yet (a new year's index)."""
    try:
        return http.get_text(url)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return None
        raise


def _doc_text(url: str) -> str:
    return http.pdf_text(url) if url.lower().endswith(".pdf") else boj.html_main_text(http.get_text(url))


def collect_boj_decisions(state: State, since: date, today: date, log: list) -> None:
    """Every policy decision from the year before `since` (for context and the
    previous rate); votes are recorded for meetings on or after `since`."""
    members = load_members(bank="BoJ", include_former=True)
    items = []
    for year in range(since.year - 1, today.year + 1):
        html = _get_or_none(boj.statement_index_url(year))
        if html:
            items += boj.parse_statement_index(html)
    previous = None
    for it in sorted(items, key=lambda x: x.date):
        if it.date > today:
            continue
        stored = {d["date"]: d for d in load_decisions("BoJ")}
        if state.seen(it.url) and it.date.isoformat() in stored:
            previous = stored[it.date.isoformat()]["decision_rate"]
            continue
        try:
            dec = boj.parse_decision(_doc_text(it.url), members)
        except Exception as e:
            log.append(f"ERROR     {it.url}: {e}")
            traceback.print_exc(file=sys.stderr)
            continue
        if dec.unmatched:
            log.append(f"ERROR     {it.url}: unknown members {dec.unmatched}; update config/members.json")
            continue
        prev = previous if previous is not None else (dec.rate if it.title.startswith("Statement") else None)
        previous = dec.rate
        if prev is None:
            state.mark(it.url, note="first decision in range is a rate change; previous rate unknown")
            continue
        rates, unknown = boj.voted_rates(dec, prev)
        announced = boj.decision_time(it.date, dec)
        save_decision({
            "bank": "BoJ", "date": it.date.isoformat(), "announced": iso_utc(announced), "url": it.url,
            "previous_rate": prev, "decision_rate": dec.rate,
            "label": split_label(prev, dec.rate, [Vote(m, r) for m, r in rates.items()]),
            "votes": rates, "absent": [m.id for m in dec.absent],
        })
        n = 0
        if it.date >= since:
            n = append_scores(vote_records("BoJ", it.date, it.url, prev, dec.rate, rates,
                                           iso_utc(announced), "the policy rate"))
        state.mark(it.url, note=f"decision {dec.rate:g}%")
        extra = f"; rate unknown for {unknown}" if unknown else ""
        log.append(f"decision  {it.date}  BoJ {dec.rate:g}%  "
                   f"{split_label(prev, dec.rate, [Vote(m, r) for m, r in rates.items()]):<16} {n} votes recorded{extra}")


def collect_boj_speeches(state: State, since: date, today: date, log: list) -> None:
    members = load_members(bank="BoJ")
    for year in range(since.year, today.year + 1):
        html = _get_or_none(boj.speech_index_url(year))
        for item in boj.parse_speech_index(html or ""):
            if item.date < since or state.seen(item.url):
                continue
            member = boj.attribute_speaker(item.speaker, members)
            if member is None:
                state.mark(item.url, note=f"not a Policy Board member: {item.speaker.split(',')[0]}")
                continue
            try:
                pdf = boj.speech_pdf_url(http.get_text(item.url))
                if pdf is None:
                    raise ValueError("no speech PDF linked")
                text = boj.clean_en_pdf_text(http.pdf_text(pdf))
                doc = {
                    "id": boj.speech_doc_id(item), "bank": "BoJ", "kind": "speech",
                    "member_id": member.id, "speaker_name": item.speaker.split(",")[0],
                    "title": item.title, "description": item.speaker, "url": item.url, "text_url": pdf,
                    "published": iso_utc(boj.speech_time(item.date)), "delivered_date": item.date.isoformat(),
                    "source_type_hint": "speech", "language": "en", "text_source": "pdf",
                    "text": text, "collected_at": utc_now_iso(),
                }
                write_raw(doc)
                state.mark(item.url, [doc["id"]])
                log.append(f"speech    {item.date}  {member.id:<12} {item.title[:70]}")
            except Exception as e:
                log.append(f"ERROR     {item.url}: {e}")
                traceback.print_exc(file=sys.stderr)


def collect_boj_press(state: State, since: date, today: date, log: list) -> None:
    """Press conferences, Japanese only. Dated by the conference, not publication."""
    from datetime import datetime
    members = load_members(bank="BoJ")
    for year in range(since.year, today.year + 1):
        html = _get_or_none(boj.press_index_url(year))
        for item in boj.parse_press_index(html or "", members):
            try:
                d = date(year, item.month, item.day)
            except ValueError:
                continue
            if d < since or d > today or state.seen(item.url):
                continue
            if item.member is None:
                state.mark(item.url, note=f"speaker not matched: {item.title}")
                continue
            try:
                text = boj.clean_ja_text(_doc_text(item.url))
                when = boj.press_datetime(text) or datetime.combine(d, boj.DECISION_TIME, tzinfo=boj.TOKYO)
                doc = {
                    "id": boj.press_doc_id(item, d), "bank": "BoJ", "kind": "press_conference",
                    "member_id": item.member.id, "speaker_name": item.member.name,
                    "title": item.title, "description": "Press conference (Japanese)", "url": item.url,
                    "text_url": item.url, "published": iso_utc(when), "delivered_date": d.isoformat(),
                    "source_type_hint": "press_conference", "language": "ja",
                    "text_source": "pdf" if item.url.endswith(".pdf") else "html",
                    "text": text, "collected_at": utc_now_iso(),
                }
                write_raw(doc)
                state.mark(item.url, [doc["id"]])
                log.append(f"press     {d}  {item.member.id:<12} {item.title}")
            except Exception as e:
                log.append(f"ERROR     {item.url}: {e}")
                traceback.print_exc(file=sys.stderr)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", type=date.fromisoformat,
                    default=date.today() - timedelta(days=DEFAULT_LOOKBACK_DAYS))
    ap.add_argument("--bank", choices=["BoE", "BoJ", "all"], default="all")
    args = ap.parse_args(argv)

    state = State()
    log: list[str] = []
    today = date.today()
    steps = []
    if args.bank in ("BoE", "all"):
        steps += [("BoE minutes", lambda: collect_boe_minutes(state, args.since, today, log)),
                  ("BoE speeches", lambda: collect_boe_speeches(state, args.since, log))]
    if args.bank in ("BoJ", "all"):
        steps += [("BoJ decisions", lambda: collect_boj_decisions(state, args.since, today, log)),
                  ("BoJ speeches", lambda: collect_boj_speeches(state, args.since, today, log)),
                  ("BoJ press conferences", lambda: collect_boj_press(state, args.since, today, log))]
    for name, step in steps:
        try:
            step()
        except Exception as e:  # one source failing must not stop the others
            log.append(f"ERROR     {name}: {e}")
            traceback.print_exc(file=sys.stderr)
        state.save()

    print(f"Collected since {args.since}:")
    print("\n".join(log) if log else "  nothing new")
    return 1 if any(line.startswith("ERROR") for line in log) else 0


if __name__ == "__main__":
    sys.exit(main())
