# Hawk/Dove Scoring Rubric

**Version:** v1 (19 Oct 2026)
**Built from:** 126 statements labelled by Ollie (gold set v1.1), 99 train / 24 holdout / 3 retired
**Tested:** v0 blind test on 27 holdout statements: 37% exact, 78% within 1 point, average gap 1.0, scorer 0.6 points too dovish
**Applies to:** Bank of England MPC, Bank of Japan Policy Board

This file is the instruction set the scorer follows for every statement. Anchor
examples are drawn only from the training split, so the holdout stays a fair test.

---

## 1. Purpose and scope

Score a single statement by one policymaker for what it signals about **their
preferred path for the policy rate**.

In scope: views on the rate path, the pace of moves, the neutral rate, inflation
persistence, the balance of risks, and the policy stance (tight, restrictive,
accommodative). For the BoJ, also JGB purchases where tied to the stance.

Out of scope, return `not_policy`: financial stability, payments, regulation,
CBDC, AI, institutional history, unless the speaker ties it to the rate path.

## 2. Reference frame (the most important rule)

**Hawkish means wanting tighter policy than markets currently expect. Dovish
means wanting looser policy than markets currently expect.**

Every scoring call is given a context block:

```
Bank:                 BoE
Date:                 2026-09-24
Policy rate:          3.75%
Last decision:        hold, 6-3 (3 for a hike)
Market-implied path:  +97bp over 12 months (from baseline_<date>.json)
Speaker's last vote:  hold
```

Score against that block, not against an absolute idea of tight or loose.
The same words can score differently in different contexts.

## 3. The scale

Whole numbers only. If torn between two levels, choose the one closer to 0 and
lower the confidence.

| Score | Meaning | Example from the gold set |
|---|---|---|
| **+5** | Votes for a hike against the majority, or explicitly calls for an immediate hike larger than expected. **Votes and explicit calls only.** | Pill, Greene, Mann: voted to raise Bank Rate to 4% against a 6-3 hold (Sep 2026) |
| **+4** | Argues for tightening now or very soon, or that policy is clearly too loose | Mann: "our current monetary policy stance is not sufficiently tight"; Masu: "desirable to raise the policy rate at the earliest stage possible"; Tamura: "accelerate the pace of rate hikes without hesitation" |
| **+3** | Argues further tightening is likely needed, or should come sooner than markets expect | Pill: "a prompt but modest hike in bank rate will help mitigate upside risks"; Greene: "Waiting for definitive evidence... would leave policy behind the curve" |
| **+2** | Clear hawkish tilt: inflation persistence is the main concern, upside risks stressed, conditional case for tightening | Ramsden: "risks to the inflation outlook... have tilted more to the upside"; Breeden: "if risks... crystallise, it becomes increasingly appropriate for Bank Rate to respond" |
| **+1** | Leans hawkish: mild upside-risk language, readiness to act | Bailey: "we are ready to adjust course as needed"; Takata: "the Bank will need to adopt a nimble approach" |
| **0** | Balanced, purely data-dependent, or the Governor restating the expected path | Ueda: "the Bank will continue to raise the policy interest rate at an appropriate pace" |
| **-1** | Leans dovish: caveats, mild downside or balancing language | Taylor: "an extended hold at this level is... the correct and appropriately measured policy response" |
| **-2** | Clear dovish tilt: prefers waiting, growth concerns, inflation not persistent, or wants hikes to stop short of neutral | Dhingra: "continue to see value in waiting for a clearer read"; Takata: "the Bank should not aim to reach the expected neutral interest rate" |
| **-3** | Argues policy is tight enough, or easing should come sooner than markets expect | Taylor: "interest rates can and should resume their downward path to neutral"; Bailey: "the paths would point to a looser policy stance than implied by the market curve" |
| **-4** | Argues against the next expected move, or for easing soon | Asada: "a rate hike could slow the economy" (Jul 2026, between two dissents against hikes) |
| **-5** | Votes against a hike or for a cut against the majority, or explicitly calls for immediate easing. **Votes and explicit calls only.** | Asada: voted against the hike to 1.25% (Sep 2026) |

## 4. Signal dimensions

Read the statement on these dimensions, then combine. The rate-path signal
dominates: if a statement states a rate preference, that largely sets the score.

1. **Rate path preference** (explicit, implied, or none)
2. **Inflation assessment** (persistence, second-round effects, expectations)
3. **Growth and labour market**
4. **Balance of risks**
5. **Bank-specific:** BoE quantitative tightening pace; BoJ JGB purchases, yields, yen

## 5. Interpretation rules

These come from the calibration round. Each one fixes a mistake made at least once.

1. **Score the meaning, not the keywords.** Negation flips the sign. "I do not
   draw much comfort from the relatively benign developments" is hawkish: the
   speaker refuses to be reassured by soft data. Never score on words like
   "benign", "comfort" or "risk" alone.
2. **"Neutral" depends on which side of neutral the rate is.** The BoJ is below
   neutral, so "move closer to neutral" means hikes (hawkish). The BoE is above
   neutral, so "resume the downward path to neutral" means cuts (dovish). Check
   the context block before scoring any statement about neutral.
3. **Policy jargon has a direction.** "Activist move", "risk management
   strategy", "lean against", "act decisively" and "behind the curve" all point
   to tightening when inflation is the concern. "Look through", "patience",
   "extended hold" and "more than sufficient" point to holding or easing.
4. **Inflation persistence is hawkish.** A statement that inflation will stay
   above target, or that price rises "may not be temporary", scores positive
   even if it names no rate path.
5. **Conditionals score one level below the same view stated outright.**
   "If the conflict persists, policy may have to tighten" scores +2, where
   "policy will have to tighten" would score +3. "I would stand ready to react,
   forcefully if necessary" scores +3. A conditional in both directions
   ("risks are two-sided") scores 0 or +/-1.
6. **The ends of the scale are for votes and explicit calls.** Strong speech
   caps at +/-4. Only a recorded dissent, or an explicit call for an immediate
   move, earns +/-5.
7. **The Governor restating the expected path scores 0; anyone else arguing
   for it scores +/-2.** When Ueda says the Bank "will continue to raise the
   policy interest rate", he is describing committee policy: 0. When a deputy
   or board member says the Bank "should continue to raise" or "needs to
   continue to raise", they are taking a side: +2. The same applies in the
   dovish direction.
8. **Governors and deputies often speak for the committee.** Flag these
   statements as `institutional`. They keep their score, but the dashboard can
   weight or display them differently.
9. **Paraphrases score the same way but with lower confidence.** A reporter's
   summary carries less information than the speaker's own words.
10. **Score the words, not the speaker's reputation.** A known dissenter
    backing staged hikes is still backing hikes. Their votes already carry
    their stance into the dashboard, so the words must be scored on their own.
11. **Wanting hikes to stop short of neutral is dovish, even alongside support
    for near-term hikes.** "Gradual hikes rather than aiming for neutral" scores
    -2: the cap on where rates end up is the signal, and the near-term hikes
    are already expected.
12. **Fragments and unclear subjects.** If a statement is a fragment, or its
    subject is unclear ("if it were to materialise"), score it from the clear
    part at lower confidence. Use `need_context` only when the direction itself
    cannot be read.

## 6. Bank glossaries

Stock phrases and what they usually signal. Each entry is dated because usage
drifts. Extend these during calibration.

**Bank of England**

| Phrase | Usual signal | Noted |
|---|---|---|
| "gradual and careful" | Neutral to slightly dovish vs a market pricing hikes | Oct 2026 |
| "second-round effects" | Hawkish when the speaker worries about them, dovish when dismissing them | Oct 2026 |
| "look through" (energy prices) | Dovish | Oct 2026 |
| "restrictive" (current stance) | Dovish: implies no need to tighten further | Oct 2026 |
| "risk management" | Hawkish: case for acting before the evidence is in | Oct 2026 |

**Bank of Japan**

| Phrase | Usual signal | Noted |
|---|---|---|
| "adjust the degree of monetary accommodation" | Hike, framed as not a tightening | Oct 2026 |
| "accommodative financial conditions" | Hawkish: room to keep hiking | Oct 2026 |
| "appropriate pace" | Neutral: the expected path | Oct 2026 |
| "not at a fixed pace", "nimble" | Slightly hawkish: open to faster moves | Oct 2026 |
| "negative real interest rate" | Hawkish: real rates too low | Oct 2026 |
| "underlying inflation below 2%" | Dovish: case against hiking | Oct 2026 |

## 7. Output schema

Return exactly this JSON for each statement:

```json
{
  "score": -2,
  "confidence": 0.7,
  "flag": null,
  "rate_path_signal": "explicit | implied | none",
  "dimensions": {"inflation": -1, "growth": -2, "risks": -1},
  "topics": ["wages", "labour_market"],
  "key_quote": "short excerpt, under 40 words",
  "rationale": "one sentence on why this score",
  "institutional": false,
  "novelty": "new | repeated"
}
```

`flag` is `null`, `"not_policy"` or `"need_context"`. When `flag` is set,
`score` is `null`.

## 8. Version log

| Version | Date | Change | Prompted by |
|---|---|---|---|
| v0 | 2026-10-19 | First draft. Scale anchors, rules 1 to 9, glossaries. +/-5 reserved for votes and explicit calls. | Ollie's 126 labels and corrections to 9 of them |
| v1 | 2026-10-19 | Rule 5: conditionals one level below, not half. Rule 7: Governor restating path = 0, others arguing for it = +/-2. New rules 10 (words not reputation), 11 (stopping short of neutral = -2), 12 (fragments). -2 and -4 anchors updated. | v0 blind test: scorer too dovish on BoJ hike language and conditionals; disagreements on Takata and Sato |

## Open questions for v2

Settled in v1: the same words from different speakers (now rule 7).

Still open:

1. **Asada's June dissent** is labelled -4, but rule 6 makes a dissent against
   a hike -5. Should every dissent be +/-5?
2. **Balancing caveats inside a hawk's speech.** Pill's "events in the Gulf
   have not triggered a de-anchoring" is labelled -3. Should a reassurance
   clause from a hawk count that strongly, or cap at -1?
3. **Dhingra headline** ("very hard to say... it depends on energy prices") is
   labelled +2. It reads as 0. Keep or change?
4. **Deputy governors under rule 7.** v1 treats deputies like board members
   (arguing for the path = +2) because Himino's labels support it. Confirm.
