# Scorer instructions

You turn collected documents into scored passages. You follow `rubric.md`
exactly; this file says how to apply it to whole documents and what to write.

Read `rubric.md` in full before scoring anything, every run. It is the only
source of scoring rules. If this file and the rubric ever disagree, the rubric
wins.

## 1. Find the work

```
python -m pipeline.pending --limit 15
```

This lists documents in `data/raw/` with no scored passages under the current
rubric version, newest first. For each it prints the document path, the
speaker, the source type hint, the context block, and the speaker's most recent
scored passages (for judging novelty). Score at most 15 documents per run;
leave the rest for the next run.

## 2. For each document

Open the document JSON. The text is in `text`.

### 2a. Confirm the source type

Start from `source_type_hint`. Change it only by the rules in
`docs/WEIGHTING.md` section 4 (for example, Q&A after a speech that adds a
distinct position is a `comment`; slides with no spoken words are still the
speech type but usually yield no passages). Written statements in BoE minutes
are always `minutes_statement`.

### 2b. Split into passages

Follow `docs/EXTRACTION.md` step 3:

- A passage is one to three consecutive sentences making one point.
- Keep passages about the rate path, the policy stance, inflation persistence,
  the balance of risks, or the neutral rate (rubric section 1).
- Drop history, methodology, thanks, references, and other topics (payments,
  regulation, financial stability) unless the speaker ties them to the rate
  path.
- Aim for 3 to 8 passages per speech. A written statement in the minutes
  usually gives 2 to 4. Prefer the passages that carry the speaker's own view
  over ones describing data or the committee's forecast.
- Copy each passage **verbatim** from `text`. Do not fix typos, join
  non-adjacent sentences, or paraphrase. The validator rejects any passage it
  cannot find in the document.

If the document has no passage in scope (a speech on payments, say), write one
record for the whole document with `flag: "not_policy"`, `score: null`, the
title as `passage`, and `passage_weight_share: 0`. This marks the document as
done so it is not picked up again.

### 2c. Score each passage

Score each passage on its own against the document's context block, by the
rubric: the reference frame (section 2), the scale (section 3), the dimensions
(section 4), every interpretation rule (section 5) and the glossaries
(section 6). Read neighbouring sentences to understand a passage, but score
only what the passage itself says.

If the context block says the market-implied path is not available, score
against the policy rate and last decision, and lower confidence by 0.1.

### 2d. Share the document's weight

Each document carries its source weight once in total (EXTRACTION.md step 3).
Give each scored passage (flag `null`) an equal share: 1 divided by the number
of scored passages in that document, rounded to 4 decimal places, with the last
passage taking the remainder so the shares sum to exactly 1. Flagged passages
get 0.

## 3. Write the records

Write one JSON object per line to a new file, `data/scores/incoming.jsonl`,
then validate and append it:

```
python -m pipeline.validate --append data/scores/incoming.jsonl
```

This checks every record, refuses the whole file if any record fails, and
otherwise moves the records into `data/scores/YYYY-MM.jsonl` and deletes the
incoming file. Fix and rerun on failure; never edit the monthly files by hand.

### Record format

```json
{
  "id": "boe-speech-2026-09-24-clare-lombardelli-speech-at-the-sixth-biennial-conference-poland-p03",
  "document_id": "boe-speech-2026-09-24-clare-lombardelli-speech-at-the-sixth-biennial-conference-poland",
  "member_id": "lombardelli",
  "bank": "BoE",
  "timestamp": "2026-09-24T08:00:00Z",
  "source_type": "speech",
  "document_url": "https://www.bankofengland.co.uk/speech/...",
  "passage": "verbatim text from the document",
  "language": "en",
  "context": {"policy_rate": 3.75, "last_decision": "hold, 6-3 (3 for a hike)", "baseline_file": null},
  "score": -1,
  "confidence": 0.7,
  "flag": null,
  "rate_path_signal": "implied",
  "dimensions": {"inflation": 0, "growth": -1, "risks": 0},
  "topics": ["energy", "second_round_effects"],
  "key_quote": "short excerpt, under 40 words",
  "rationale": "one sentence on why this score",
  "institutional": true,
  "novelty": "new",
  "rubric_version": "v1",
  "passage_weight_share": 0.25
}
```

- `id`: the document id, then `-p` and a two-digit passage number in document order.
- `timestamp`, `document_url`, `member_id`, `bank`, `language`: from the document
  (`published`, `url`, and so on).
- `context`: copy `policy_rate`, `last_decision` and `baseline_file` from the
  context printed by `pipeline.pending`.
- `score` to `novelty`: the rubric's output schema (section 7). `score` is null
  exactly when `flag` is set.
- `institutional`: true for the Governor and deputies speaking for the committee
  (rubric rule 8).
- `novelty`: `repeated` if the speaker made the same point in one of the recent
  passages listed by `pipeline.pending`, otherwise `new`.
- `rubric_version`: the version at the top of `rubric.md`.
- `topics`: short lower-case tags from this list where they fit, others only if
  none does: `inflation_persistence`, `second_round_effects`, `wages`,
  `labour_market`, `growth`, `energy`, `inflation_expectations`, `neutral_rate`,
  `rate_path`, `policy_stance`, `balance_of_risks`, `qt`, `jgb_purchases`, `yen`,
  `financial_conditions`, `fiscal`, `global`, `trade`.

## 4. Do not

- Score votes. They are scored by rule in `pipeline/votes.py` during collection.
- Change a score already written. A rubric change means a rescore under the new
  version, which keeps the old records (CLAUDE.md, Working with Ollie).
- Look at Ollie's calibration labels while scoring a blind test.
