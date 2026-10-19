# Source Map

Every source the scrapers collect, per bank. "Verified" means the URL was
opened and its structure checked on 19 Oct 2026. "Unverified" means the
pattern is expected but must be checked in the build before relying on it.

All times are stored in UTC. Display converts to London or Tokyo time.

## Network allowlist for the routine environment

The routine's cloud environment must allow these domains (Custom network
access, with the default package-manager list kept on):

```
www.bankofengland.co.uk
www.boj.or.jp
www.bis.org
committees.parliament.uk
```

Add later, for the news tier: `news.google.com`, `api.gdeltproject.org`.

## Bank of England

| Source | URL | Format | Cadence | Weight type | Status |
|---|---|---|---|---|---|
| Speeches feed | https://www.bankofengland.co.uk/rss/speeches | RSS, latest 50 items, links to HTML page; full text is usually a linked PDF | Check every run | `speech` (or `comment` for fireside chats and panels) | Verified |
| Speech page | https://www.bankofengland.co.uk/speech/YYYY/month/slug | HTML summary plus PDF link | On new feed item | as above | Verified |
| Monetary Policy Summary and Minutes | https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/YYYY/month-YYYY (PDF: /-/media/boe/files/monetary-policy-summary-and-minutes/YYYY/monetary-policy-summary-and-minutes-month-YYYY.pdf) | HTML and PDF | 8 times a year, see `config/calendar.json` | Votes (`dissent_vote`, `majority_vote`) plus each member's written statement (`minutes_statement`) | Verified |
| MPR press conference opening remarks | https://www.bankofengland.co.uk/-/media/boe/files/monetary-policy-report/YYYY/month/opening-remarks-month-YYYY.pdf | PDF | 4 times a year (Feb, Apr or May, Jul or Aug, Nov) | `press_conference` | Verified (July 2026) |
| Treasury Select Committee hearings | https://committees.parliament.uk/work/8621/ (inquiry page; transcripts under /oralevidence/{id}/html) | HTML transcript | After each MPR, published days later | `testimony` | Verified (inquiry page) |

**Fields to extract:** speaker, date, title, venue, URL, full text. For
minutes: meeting end date, decision, vote split, each member's vote and the
rate they voted for, and each member's written statement.

**Notes:**
- From 2026 the minutes include a short written statement from each member.
  These are the richest single source per meeting: one per member, eight
  times a year.
- The RSS feed covers all Bank staff. Filter to the nine MPC members by name
  (see `config/members.json`).

## Bank of Japan

| Source | URL | Format | Cadence | Weight type | Status |
|---|---|---|---|---|---|
| Speeches index (English) | https://www.boj.or.jp/en/about/press/koen_YYYY/index.htm | HTML list | Check every run | `speech` | Verified |
| Speech full text (English) | https://www.boj.or.jp/en/about/press/koen_YYYY/data/koYYMMDDa1.pdf | PDF | On new index item | `speech` | Verified |
| Statement on Monetary Policy | https://www.boj.or.jp/en/mopo/mpmdeci/state_YYYY/index.htm (files: /en/mopo/mpmdeci/mpr_YYYY/kYYMMDDa.pdf) | PDF (occasionally HTML) | 8 meetings a year | Votes; names dissenters and what each proposed | Verified |
| Governor's press conference | Expected under https://www.boj.or.jp/en/about/press/kaiken_YYYY/ | HTML | Day after each meeting (English translation later) | `press_conference` | Unverified |
| Board member press conferences after regional speeches | Expected on the same speech pages or in Japanese only | HTML | After regional speeches | `press_conference` | Unverified, often Japanese only |
| Summary of Opinions | https://www.boj.or.jp/en/mopo/mpmsche_minu/opinion_YYYY/ | PDF | About 8 working days after each meeting | Not attributed to members. Use for context only, never as a member's data point | Verified (index) |
| Minutes | https://www.boj.or.jp/en/mopo/mpmsche_minu/minu_YYYY/ | PDF | After the following meeting | Votes and proposals, already captured from the Statement | Verified (index) |

**Fields to extract:** as BoE. For Statements: decision, vote tally, each
dissenter's name and proposal.

**Notes:**
- Only dissenters are named. Every board member not named is recorded as
  voting with the majority (see `EXTRACTION.md` for when majority votes count).
- Japanese versions often publish first. Store the first publication time;
  score the English text when available, the Japanese otherwise (flag
  `language: ja`).
- Speech index URLs can carry codes that don't match the date. Take the date
  from the index entry, not the filename.

## Backfill

| Source | URL | Notes | Status |
|---|---|---|---|
| BIS central bankers' speeches | https://www.bis.org/pages/download-central-bankers-speeches/speeches-YYYY.zip | UTF-8 text files, comma-delimited, 1996 to 2026, updated regularly (last 1 Jul 2026). Also via the `gingado` Python library. | Verified |
| Official archives | The BoE and BoJ pages above, for earlier years | Slower but complete, with votes | Verified patterns |

**Licence check needed:** the BIS permits use "for noncommercial purposes".
An internal tool at a commercial firm may not count. Until that is
confirmed, backfill from the official BoE and BoJ archives, and use the BIS
set only to cross-check coverage.

## Market baseline (Bloomberg, manual)

| Source | Route | Cadence | Status |
|---|---|---|---|
| SONIA OIS (BPSWS1Z, BPSWSC, BPSWSF, BPSWS1, BPSWS2 Curncy) | BQNT, BQL `px_last`, copied out as CSV | Weekly, plus the day before each meeting | Verified; export approved by Bloomberg |
| TONA OIS (JYSO1Z, JYSOC, JYSOF, JYSO1, JYSO2 Curncy) | as above | as above | Verified |

Save each pull as `data/baseline/ois_YYYY-MM-DD.csv`. `engine/baseline.py`
turns it into the expected path. The scorer uses the most recent baseline
dated on or before the statement.

## Later: news tier (weight 1)

Google News RSS per member name, and GDELT. Not in v1.
