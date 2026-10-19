"""
Check every source, save new documents to data/raw/, score votes by rule into
data/scores/, and record what has been seen in data/state.json.

    python -m pipeline.collect                 # new items from the last 92 days
    python -m pipeline.collect --since 2026-01-01

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

from . import boe, http
from .members import load_members
from .store import ROOT, State, append_scores, iso_utc, save_decision, utc_now_iso, write_raw
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


def boe_vote_records(announcement: date, url: str, minutes: boe.Minutes) -> list[dict]:
    votes = [Vote(v.member.id, v.voted_rate) for v in minutes.votes if v.member]
    label = split_label(minutes.previous_rate, minutes.decision_rate, votes)
    ts = iso_utc(boe.minutes_release_time(announcement))
    out = []
    for sv in score_meeting(minutes.previous_rate, minutes.decision_rate, votes):
        out.append({
            "id": f"boe-{announcement.isoformat()}-vote-{sv.member_id}",
            "member_id": sv.member_id,
            "bank": "BoE",
            "timestamp": ts,
            "source_type": sv.source_type,
            "document_url": url,
            "passage": f"Voted for Bank Rate at {sv.voted_rate:g}%; decision {minutes.decision_rate:g}% ({label}).",
            "language": "en",
            "context": {"policy_rate": minutes.previous_rate, "last_decision": label},
            "vote": {"previous_rate": minutes.previous_rate,
                     "decision_rate": minutes.decision_rate,
                     "voted_rate": sv.voted_rate},
            "score": sv.score,
            "confidence": 1.0,
            "flag": None,
            "rationale": sv.rationale,
            "rubric_version": VOTE_RULE_VERSION,
            "passage_weight_share": 1.0,
        })
    return out


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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", type=date.fromisoformat,
                    default=date.today() - timedelta(days=DEFAULT_LOOKBACK_DAYS))
    args = ap.parse_args(argv)

    state = State()
    log: list[str] = []
    today = date.today()
    collect_boe_minutes(state, args.since, today, log)
    collect_boe_speeches(state, args.since, log)
    state.save()

    print(f"Collected since {args.since}:")
    print("\n".join(log) if log else "  nothing new")
    return 1 if any(line.startswith("ERROR") for line in log) else 0


if __name__ == "__main__":
    sys.exit(main())
