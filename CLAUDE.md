# Central Bank Hawk/Dove Monitor

A live dashboard placing each voting member of the Bank of England MPC and the
Bank of Japan Policy Board on a hawk/dove scale, updated as they speak and
vote. Clicking a member opens a timeline of their scored statements and votes.

**Owner:** Ollie. **Audience for v1:** internal at Deepwell (not clients).
**Runs on:** Claude Code routines on Ollie's Claude plan. There is no separate
API key; scoring happens inside the routine session.

Read this file first, then the files it points to. Ask before changing any
decision in the Decisions section.

## How it works

```
Scrapers (Python)        Routine session (Claude)          Engine (Python)            Dashboard
BoE / BoJ official  -->  extract passages, score with  -->  decay + weights  -->  stances.json  -->  artifact page
sites, every run         rubric.md, write JSONL             per member              + timelines
                                        ^
                   Bloomberg OIS baseline (manual CSV, weekly)
```

1. **Collect.** `python -m pipeline.collect` checks every source in
   `docs/SOURCES.md`, saves new documents to `data/raw/`, and records what it
   has seen in `data/state.json`. Votes are parsed here and scored by rule.
2. **Extract and score.** The routine session reads each new document and
   follows `docs/EXTRACTION.md` and `rubric.md` to write scored passages to
   `data/scores/YYYY-MM.jsonl`. `python -m pipeline.validate` checks every
   record against the schema before anything is committed.
3. **Compute.** `python -m engine.compute` runs `engine/decay.py` over all
   data points and writes `data/stances.json` (current stance, signal
   strength, held status, 30 and 90 day momentum) and per-member timelines.
4. **Publish.** The dashboard is updated from `data/stances.json`.
5. **Commit.** Data changes are committed so every score has an audit trail.

## Files

| Path | What it is | Status |
|---|---|---|
| `rubric.md` | Scoring rules. The scorer follows this exactly. | v1, calibrated |
| `docs/WEIGHTING.md` | Source weights and how to classify each data point | Done |
| `docs/EXTRACTION.md` | Raw document to scored passages; vote scoring rules | Done, 2 decisions open |
| `docs/SOURCES.md` | Every source, URL, format, cadence, network allowlist | Done, some URLs unverified |
| `config/members.json` | 18 members: roles, terms, name variants, Japanese names | Done, several dates to verify |
| `config/calendar.json` | Meeting dates 2026 and 2027, both banks | Verified |
| `engine/decay.py` | Time decay (linear to zero over 10 months, hold when silent), weights, stance, momentum, timeline | Built, 16 tests pass |
| `engine/test_decay.py` | Tests, including that weights match the agreed ratios | Passing |
| `engine/baseline.py` | Bloomberg OIS CSV to market-implied path | Built |
| `data/baseline/` | OIS pulls from BQNT, one CSV per date | One file (16 Oct 2026) |
| `data/calibration/gold_set_v1.json` | Ollie's 126 labelled statements: 99 train, 24 holdout, 3 retired | Done |
| `data/calibration/scores_v0.json` | Blind test of rubric v0 on the holdout | 78% within 1 point |
| `tools/calibration-lab.html` | Source of the labelling page (live at https://claude.ai/artifact/NAgbLfJ94jJNGsC1cq45Re) | Live |
| `tools/bqnt/` | BQNT feasibility notebook | Done |

## Decisions (do not change without asking Ollie)

- **Scale:** whole numbers from -5 (dovish) to +5 (hawkish). +/-5 only for
  votes and explicit calls for an immediate move.
- **Reference frame:** hawkish or dovish relative to what markets expect, from
  the OIS baseline.
- **Weights:** dissent 18, vote 12, speech 6, press conference 6, testimony 6,
  comment 5, interview 5, podcast 5, news 1.
- **Decay:** linear from full weight to zero over 304 days (10 months). A
  member with no live data points holds their last position.
- **Majority votes:** recorded only at split meetings.
- **Timestamps:** stored in UTC.
- **Hosting and cost:** Claude Code routines on Ollie's plan; no API key.
- **Bloomberg:** used only for the OIS baseline, copied out of BQNT manually.
  Bloomberg confirmed this export is fine. BQNT cannot reach the internet, so
  nothing else runs there.
- **Audience:** internal only. No client-facing output in v1.

## Build phases

Work through these in order. Each ends with something Ollie can check.

**Phase 0: Setup**
- Private GitHub repo containing this folder. Tests pass (`pytest engine/`).
- Add `minutes_statement` (proposed weight 6) to `SOURCE_WEIGHTS` and the ratio test.
- Add the passage weight share from `EXTRACTION.md` to `DataPoint`.

**Phase 1: BoE collection**
- Collectors for the speeches RSS feed (with PDF text extraction) and the MPC
  minutes (votes and each member's written statement).
- Verify every URL marked unverified in `SOURCES.md`, and the member dates
  marked verify in `members.json`.
- Check: a list of the last 3 months of BoE documents and votes, attributed to members.

**Phase 2: Scoring**
- `prompts/score.md`: the scorer instructions, built from `rubric.md` with the
  context block and output schema.
- `pipeline/validate.py`: rejects records that don't match the schema.
- **Fresh blind test of rubric v1.** Ollie labels about 30 new statements in
  the Calibration Lab; a session that has not seen his labels scores them;
  `eval/compare.py` reports exact match, within 1 point, average gap, bias and
  rank agreement. Target: at least 85% within 1 point. If it falls short,
  revise the rubric with Ollie and bump the version.
- Check: the comparison report.

**Phase 3: Engine**
- `engine/compute.py`: stances, momentum, timelines, held status, signal
  strength. Implement the majority-vote rule and passage weight share.
- Check: `data/stances.json` for the BoE that Ollie can sanity-check against
  his own reading.

**Phase 4: Dashboard v1**
- One page per bank: a horizontal dove-to-hawk axis with each member placed by
  stance, an arrow for 30-day momentum, faded when stale and badged "held
  since" when held, the committee median marked, a strip of the last 8 votes,
  and a ticker of the newest scored statements.
- Clicking a member expands a timeline: the stance line over time, a dot per
  scored passage coloured by score, diamonds for votes (dissents highlighted).
  Clicking a dot shows the quote, date, source link, score and rationale.
  Filter by topic.
- Visual direction: the dark, terminal-style look of the weighting pyramid
  (IBM Plex, amber for hawk, blue for dove). Must look better than
  Bloomberg's central bank dashboards.
- Publish as a Claude artifact. **Check first** how a routine can update it:
  writing to the artifact's database is preferred; republishing the page with
  embedded data is the fallback. Confirm which works from a routine session.
- **Check with Ollie:** whether his Deepwell colleagues are in the same
  claude.ai organisation. Artifacts that keep data can only be opened by
  members of the owner's organisation. If they aren't, host the page
  elsewhere (a static host) and have the routine push `stances.json` there.

**Phase 5: Routines**
- Cloud environment with Custom network access: the domains in
  `SOURCES.md`, plus the default package list.
- Routine "collect-and-score": weekdays, every 2 hours (more often is not
  needed; minimum allowed is hourly). Prompt: run collect, score new
  documents per `prompts/score.md`, validate, compute, update the dashboard,
  commit. Self-contained, because each run starts fresh.
- Routines are a research preview and draw on Ollie's plan allowance. Keep
  runs small: if more than 15 documents are waiting, score the newest 15 and
  leave the rest for the next run.
- Check: a week of runs with no failures in the run list.

**Phase 6: BoJ collection**
- Speeches index and PDFs, Statements on Monetary Policy (dissents and
  proposals), governor's press conference. Handle Japanese-first publication.

**Phase 7: Backfill**
- Two years of official BoE and BoJ archives, in batches of about 20
  documents per run, so it doesn't exhaust the plan allowance.
- Do not use the BIS speeches dataset until its licence ("noncommercial
  purposes") is confirmed for internal use at a commercial firm. It can be used
  to cross-check coverage.

**Later, not v1:** news tier (weight 1) from Google News RSS and GDELT; a BQNT
app view for Terminal users (first test whether files can be uploaded into
BQNT); more banks (Fed next, then ECB).

## Open questions

Settle these with Ollie when the phase that needs them comes up:

1. Rubric: should every dissent be +/-5? (Asada's June dissent is labelled -4.)
2. Rubric: should a hawk's reassuring caveat count at -3, or cap at -1?
3. Rubric: Dhingra's "very hard to say, depends on energy prices" headline, +2 or 0?
4. Rubric: do deputy governors count as board members under rule 7?
5. `minutes_statement` weight: 6 proposed.
6. Passage weighting: split each document's weight equally between its passages (proposed), or by confidence?
7. Are Deepwell colleagues in Ollie's claude.ai organisation? (Phase 4.)
8. BIS dataset licence for internal commercial use. (Phase 7.)

## Working with Ollie

- No em dashes anywhere: in code comments, docs, UI text or messages.
- Prefer substance over polish in explanations; be direct.
- He labels data in the Calibration Lab. When the rubric changes, bump its
  version, log the change and the reason in its version log, and rescore
  history while keeping old scores.
