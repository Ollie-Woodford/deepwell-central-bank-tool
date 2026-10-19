# Extraction Spec

How a raw document becomes the scored data points that `engine/decay.py`
consumes. Runs on every new document the scrapers collect.

```
raw document -> 1. attribute -> 2. classify -> 3. segment -> 4. dedupe
             -> 5. attach context -> 6. score (rubric.md) -> data point
```

## 1. Attribute

Decide who is speaking. Match the speaker against `name_variants` in
`config/members.json`.

- A document by a non-member (a Bank official who is not on the committee)
  is dropped.
- A document mentioning a member but written by someone else (a news story,
  another official's speech) is not that member's statement. Exception:
  direct quotes in news become `news_speculation` (weight 1), which is not in v1.
- Minutes and Statements contain several members: split them per member.

## 2. Classify the source type

Exactly one type per data point, using the definitions in
`docs/WEIGHTING.md` section 4: `dissent_vote`, `majority_vote`, `speech`,
`press_conference`, `testimony`, `comment`, `interview`, `podcast`,
`news_speculation`. Written statements in BoE minutes are `minutes_statement`.

**Decision needed in the build:** `minutes_statement` is not in the weight
table. Proposed weight: 6, the same as a speech (it is prepared, on record and
attributable). Add it to `SOURCE_WEIGHTS` and the ratio test.

## 3. Segment

A speech makes several points. Split it into the passages that say something
about policy, and score each one separately.

- A passage is one to three consecutive sentences making one point.
- Keep passages that touch the rate path, the stance, inflation persistence,
  the balance of risks or the neutral rate (rubric section 1).
- Drop history, methodology, thanks, and other topics such as payments or
  regulation.
- Aim for 3 to 8 passages per speech. Each passage becomes its own data point
  with the speech's source type and date.

**Weighting within a document:** a speech split into 6 passages should not
count six times as much as a speech split into 2. Divide the source weight
equally between the passages from one document, so each document carries its
full source weight once in total.

**Decision needed in the build:** this equal split is the proposal. Confirm,
or weight passages by the scorer's confidence instead.

## 4. Deduplicate

- The same document from two routes (RSS and an index page; the English and
  Japanese versions) is stored once, timed from its first publication.
- A news paraphrase that is later matched to the original transcript is
  replaced by the transcript (`WEIGHTING.md` edge case 1).
- Key: member id + date + source type + normalised title.

## 5. Attach context

Every passage is scored with a context block (rubric section 2):

- Policy rate on that date, and the last decision with its vote split
  (from the stored votes).
- The market-implied path: the most recent `data/baseline/` file dated on or
  before the statement.
- The speaker's own last vote.

## 6. Score

Score each passage with `rubric.md` and its output schema. Store the rubric
version with every score, so that a rubric change can trigger a rescore of
history while keeping old scores for audit.

## Votes

Votes don't go through the scorer. They are scored by rule:

| Vote | Score |
|---|---|
| Dissent for a hike | +5 |
| Dissent against a hike, or for a cut | -5 |
| Dissent for a smaller move than the majority (e.g. +25bp when the majority did +50bp) | -3 |
| Dissent for a larger move than the majority | +3 |
| Majority vote at a **split** meeting | Scored by which side it backs: with a hike majority +2, with a hold majority while others dissented for a hike -2, and so on |
| Majority vote at a **unanimous** meeting | **Not recorded** (decision of 19 Oct 2026, `WEIGHTING.md` section 6, option B) |

A unanimous majority vote carries no information about the individual and
would drag every member toward neutral, so it is skipped.

## Output record

```json
{
  "id": "boe-2026-09-24-lombardelli-03",
  "member_id": "lombardelli",
  "bank": "BoE",
  "timestamp": "2026-09-24T09:00:00Z",
  "source_type": "speech",
  "document_url": "https://...",
  "passage": "verbatim text",
  "language": "en",
  "context": {"policy_rate": 3.75, "last_decision": "hold 6-3", "baseline_file": "ois_2026-09-21.csv"},
  "score": 2,
  "confidence": 0.8,
  "flag": null,
  "rationale": "one sentence",
  "rubric_version": "v1",
  "passage_weight_share": 0.25
}
```

`engine/decay.py` reads `member_id`, `timestamp`, `score`, `source_type` and
`confidence`. The passage weight share multiplies the source weight.
