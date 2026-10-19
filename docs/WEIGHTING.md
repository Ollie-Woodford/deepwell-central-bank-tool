# Source Weighting Instructions

How much each type of data point counts when building a member's hawk/dove
stance. Applies to every bank on the dashboard. Implemented in `decay.py` as
`SOURCE_WEIGHTS`; this file is the reference for why the numbers are what they
are and how to classify each data point.

## 1. The ratios

These are the agreed relationships between source types:

| Ratio | Meaning |
|---|---|
| 1 dissenting vote = 1.5 votes | A dissent is the strongest signal a member can send |
| 1 vote = 2 speeches | A vote is an action; a speech is an argument |
| 1 speech = 1 press conference | Both are on-record, prepared and attributable |
| 1 speech = 1.2 comments | Prepared remarks outrank off-the-cuff ones |
| 1 comment = 1 interview = 1 podcast | All are attributable but less prepared |
| 1 comment = 5 news/speculation | Unverified or second-hand signals count least |

## 2. Resulting weights

Setting news/speculation as the unit (1) and solving the chain:

| Tier | Source type | Weight | Key in code |
|---|---|---|---|
| 1 | Dissenting vote | **18** | `dissent_vote` |
| 2 | Vote (with the majority) | **12** | `majority_vote` |
| 3 | Speech | **6** | `speech` |
| 3 | Press conference | **6** | `press_conference` |
| 3 | Parliamentary testimony | **6** | `testimony` (assumed equal to a speech; not in the ratios) |
| 3 | Written statement in BoE minutes | **6** (proposed) | `minutes_statement` (prepared and on record, like a speech; in code, pending confirmation) |
| 4 | Comment | **5** | `comment` |
| 4 | Interview | **5** | `interview` |
| 4 | Podcast | **5** | `podcast` |
| 5 | News / speculation | **1** | `news_speculation` |

Only the ratios matter. Multiplying every weight by the same number changes
nothing on the dashboard, because the stance is a weighted average.

## 3. Full weight of a data point

```
total weight = source weight x confidence x decay weight
```

- **Source weight:** from the table above.
- **Confidence:** 0 to 1, returned by the scorer for that statement.
- **Decay weight:** 1.0 on the day it happens, falling linearly to 0 at 10
  months (304 days). See `decay.py`.

## 4. Classifying a data point

Assign exactly one source type to each data point using these rules.

**Dissenting vote.** The member voted against the majority decision, as
recorded in the official minutes or statement (BoE MPC minutes; BoJ Statement
on Monetary Policy, which names dissenters). Also covers a dissent against a
specific proposal (e.g. a BoJ member voting against a guidance change).

**Vote (with the majority).** The member's recorded vote matched the decision.
At the BoJ, where only dissents are named, every board member not listed as a
dissenter is recorded as a majority vote.

**Speech.** Prepared remarks delivered by the member and published by the
bank or the host. The prepared text is one data point.

**Press conference.** A scheduled press conference given by the member,
including the opening statement and the Q&A. The governor's post-meeting
press conference and the press conference BoJ board members give after
regional speeches both count here. Score the whole event as one data point
unless the member says clearly different things in different answers, in
which case score each distinct position separately.

**Testimony.** Oral evidence to a parliamentary committee (Treasury Select
Committee, Diet committees). Weighted as a speech.

**Comment.** On-record remarks outside a prepared speech or press
conference: Q&A after a speech, panel discussions, brief remarks to reporters,
remarks at a conference dinner. Must be directly attributed to the member,
with their words quoted or transcribed.

**Interview.** A one-to-one interview with a media outlet, published in full
or in substantial part.

**Podcast.** An appearance on a podcast or broadcast discussion programme.

**News / speculation.** Anything not directly attributable to the member in
their own words: "sources familiar with their thinking", a reporter's
paraphrase without a direct quote, market commentary about where a member is
thought to stand, or unconfirmed reports of internal debate.

## 5. Edge cases

1. **Upgrade when the original turns up.** If a news story paraphrases a
   speech and the full text is later published, replace the news data point
   with the speech. Never keep both.
2. **Deduplicate coverage.** The same remark reported by several outlets is
   one data point, classified at the highest tier available.
3. **Speech plus Q&A.** The prepared text is a speech (6). Answers in the
   Q&A that add a distinct position are a comment (5). Answers that only
   repeat the speech add nothing and are not scored separately.
4. **Translations.** A BoJ speech published in Japanese first and English
   later is one data point, timed from the first publication.
5. **Institutional statements.** When a governor or deputy reads out the
   committee's agreed statement, it keeps its source type but is flagged
   `institutional` by the scorer.
6. **Ambiguous type.** If a data point could fit two types, choose the lower
   weight and note the reason.

## 6. Scoring votes

**Decided 19 Oct 2026: option B.** Majority votes count only at split
meetings; at unanimous meetings they are not recorded. The scoring rules are
in `docs/EXTRACTION.md` under Votes. The background to the decision follows.

A statement gets its score from the rubric. A vote needs its own rule, and
because votes carry weight 12, this rule has a large effect on the dashboard.

**Dissenting votes** are straightforward: a dissent for a hike scores +5, a
dissent for a cut or against a hike scores -5, and smaller-scale dissents
(e.g. a smaller hike than the majority) score +3 or -3.

**Majority votes** are scored relative to what the market expected before the
meeting: a decision in line with expectations scores 0; a hawkish surprise
scores positive; a dovish surprise negative.

The consequence: most meetings are in line with expectations, so most
majority votes score 0, and at weight 12 they pull members toward neutral.
Worked example: a member gives two +3 speeches, then votes with an expected,
unanimous majority twice. Their stance falls from +3.0 to +0.94.

Options:

- **A. Keep as is.** Treats voting with the majority as genuine information
  that the member is less extreme than their rhetoric suggests.
- **B. Only count majority votes at split meetings.** A majority vote is
  informative when others dissented (it shows which side the member chose);
  at unanimous meetings it is skipped.
- **C. Lower the vote weight** below speeches for majority votes, keeping 12
  only as the reference for the dissent ratio.

To be settled during calibration by checking which option best predicts
future dissents.

## 7. Changing the weights

Weights live in `SOURCE_WEIGHTS` in `decay.py`. Any change must keep the
ratios in section 1 consistent (or update them), be recorded in the
`rubric_versions` log with the reason, and pass `test_weights_match_stated_ratios`
in `test_decay.py`.
