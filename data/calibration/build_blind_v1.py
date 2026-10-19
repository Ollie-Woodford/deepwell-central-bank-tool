"""
Fresh blind test set for rubric v1 (Phase 2), built 19 Oct 2026.

None of these documents' passages are in gold_set_v1: BoE items come from the
February, March, June and July 2026 minutes statements and Taylor's 2 March
speech; BoJ items from speeches the gold set did not use (Masu Feb 2026; Koeda,
Takata, Tamura and Ueda in Oct to Dec 2025).

BoE passages are checked verbatim against data/raw and their context comes from
pipeline.context, exactly as the production scorer will see it. BoJ passages
are verbatim from the English PDFs apart from repaired PDF spacing ("a ccordance"
to "accordance"); their context is written from the BoJ Statements on Monetary
Policy (19 Sep 2025 and 30 Oct 2025: hold at 0.5%, 7-2, Takata and Tamura
proposing 0.75%; 19 Dec 2025: hike to 0.75%, unanimous; 23 Jan 2026: hold at
0.75%, 8-1, Takata proposing 1.0%). No OIS baseline exists before 16 Oct 2026,
so every item shows the market-implied path as not available.

    python data/calibration/build_blind_v1.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline.context import build_context  # noqa: E402
from pipeline.members import load_members  # noqa: E402

OUT = ROOT / "data" / "calibration" / "blind_v1_statements.json"
RAW = ROOT / "data" / "raw" / "boe"
NAMES = {m.id: (m.name, m.role) for m in load_members()}

# (member, document id, verbatim passage)
BOE = [
    ("breeden", "boe-minutes-2026-02-05-breeden",
     "I can see a case for taking out some insurance against these downside risks to inflation and think policy should be eased a little faster than implied by the current market path."),
    ("greene", "boe-minutes-2026-02-05-greene",
     "I continue to think the monetary policy stance is not materially restrictive. Finally, I believe the cost of a policy error is greater if Bank Rate follows the market path and we end up with inflation persistence versus weaker demand."),
    ("dhingra", "boe-minutes-2026-02-05-dhingra",
     "The market-implied path for Bank Rate looks too tight. The costs of making a policy mistake seem much higher on the downside, especially given weak labour demand."),
    ("pill", "boe-minutes-2026-02-05-pill",
     "In that light, I continue to favour a cautious withdrawal of policy restriction, guided by longer‑term trends rather than short‑term news."),
    ("taylor", "boe-speech-2026-03-02-speech-by-alan-taylor-getting-the-right-directions",
     "Personally, and I’ve said this many times before, I would have preferred a looser path for Bank Rate to prevent the output gap from opening and unemployment from rising further, but I recognise that real-time uncertainty means that reasonable people can reasonably disagree."),
    ("ramsden", "boe-minutes-2026-03-19-ramsden",
     "Data releases since the February Report have broadly been in line with my expectations, and suggested continuing disinflation, so I would have otherwise voted for a 25 basis point cut in Bank Rate at this meeting. The conflict has now led me to vote for a hold in Bank Rate."),
    ("mann", "boe-minutes-2026-03-19-mann",
     "Since the conflict may yield a sustained inflation shock, I see the balance between inflation and activity to have shifted away from considering a cut towards considering a longer hold, or even a hike at some point to lean against inflation persistence."),
    ("taylor", "boe-minutes-2026-03-19-taylor",
     "Given massive uncertainty around future energy prices, I currently see a high bar to hiking. I prefer to hold while we better gauge the shock."),
    ("lombardelli", "boe-minutes-2026-03-19-lombardelli",
     "I am prepared to act as needed to address any persistent inflationary effects that may emerge."),
    ("pill", "boe-minutes-2026-03-19-pill",
     "As such, the potential for second-round effects following recent events in the Middle East remains substantial, justifying caution in monetary policy setting."),
    ("greene", "boe-minutes-2026-06-18-greene",
     "These risks are asymmetric, so we should insure against the possibility of larger second-round effects until we have evidence to determine they are not materialising. A proactive hike now in Bank Rate should help anchor inflation expectations."),
    ("dhingra", "boe-minutes-2026-06-18-dhingra",
     "If the situation were to worsen, this may warrant some further tightening. But I do not see a compelling case to increase Bank Rate pre-emptively without new evidence of more intense first-round shocks."),
    ("taylor", "boe-minutes-2026-06-18-taylor",
     "Absent worse news, I cannot see a case for tightening now, and an active hold is reasonable. If the conflict resolution holds, and risks diminish, lower rates could be preferred."),
    ("pill", "boe-minutes-2026-06-18-pill",
     "Recognising the significant uncertainty that surrounds the UK inflation outlook, raising Bank Rate to 4% continues to be the most robust monetary policy response to the intensification of these risks."),
    ("breeden", "boe-minutes-2026-06-18-breeden",
     "Monetary policy should look through the direct effects of the energy shock, partially through the indirect effects and act forcefully and early against any material second-round effects. The economic environment means the chance of material second-round effects is small and, although it is early days, there has been nothing in the news since April to change that assessment."),
    ("bailey", "boe-minutes-2026-06-18-bailey",
     "Given the context at present of softness in the real economy and uncertainty around the scale and duration of the shock to energy prices, tolerating temporarily above-target inflation as part of a return to target is an appropriate way to approach the trade-off, providing inflation expectations remain contained."),
    ("lombardelli", "boe-minutes-2026-07-30-lombardelli",
     "Policy would need to be adjusted were there to be evidence of risks of significant second-round effects, including from persistently higher energy prices."),
    ("bailey", "boe-minutes-2026-07-30-bailey",
     "There is little evidence yet of second-round effects (Boxes A and B), although it is too early to take much comfort from that."),
    ("mann", "boe-minutes-2026-07-30-mann",
     "A variety of research methods concludes that Bank Rate should be higher than 3.75% to return inflation to the 2% target sustainably."),
    ("taylor", "boe-minutes-2026-07-30-taylor",
     "For me, the more likely outcomes sit between the baseline and milder scenario, albeit with a long right tail; keeping Bank rate on hold, at a higher level now than the pre-conflict implied path, gives insurance for now, before resuming cuts when and if geopolitical uncertainty clears."),
    ("ramsden", "boe-minutes-2026-07-30-ramsden",
     "If they were to crystallise, a hike in Bank Rate may be warranted. If the risks were to subside and the underlying disinflation process continued, I would consider resuming the cutting cycle."),
]

BOJ_URL = "https://www.boj.or.jp/en/about/press/"
SEP25 = "hold, 7-2 (2 for a hike) on 2025-09-19"
OCT25 = "hold, 7-2 (2 for a hike) on 2025-10-30"
JAN26 = "hold, 8-1 (1 for a hike) on 2026-01-23"
# (member, date, url, venue, policy rate, last decision, speaker's last vote, passage)
BOJ = [
    ("masu", "2026-02-06", "koen_2026/ko260206a.htm", "Speech at a meeting with local leaders", 0.75, JAN26, "hold",
     "I am convinced that continuing with further policy interest rate hikes will be needed to complete the normalization of monetary policy in Japan."),
    ("masu", "2026-02-06", "koen_2026/ko260206a.htm", "Speech at a meeting with local leaders", 0.75, JAN26, "hold",
     "At the same time, it is critical to make sure that excessive rate hikes do not disrupt the virtuous cycle of a moderate rise in prices and wages that has finally begun to gain momentum in Japan. The Bank will therefore proceed cautiously with rate hikes."),
    ("koeda", "2025-11-20", "koen_2025/ko251120a.htm", "Speech at a meeting with local leaders", 0.5, OCT25, "hold",
     "Even if the negative range of the real interest rate narrows slightly, I believe that it is highly likely that financial conditions will continue to be accommodative, thereby continuing to stimulate consumption and investment."),
    ("koeda", "2025-11-20", "koen_2025/ko251120a.htm", "Speech at a meeting with local leaders", 0.5, OCT25, "hold",
     "Given that real interest rates are currently at significantly low levels, I believe that the Bank needs to proceed with interest rate normalization -- that is, to return real interest rates to a state of equilibrium -- so as to avoid creating unintended distortions in the future."),
    ("takata", "2025-10-20", "koen_2025/ko251020a.htm", "Speech at a meeting with business leaders", 0.5, SEP25, "hike to 0.75%",
     "Considering that the once deeply entrenched norm has waned in Japan, that the price stability target has been almost achieved, and that the \"planned suspension\" approach can be lifted reflecting fewer concerns over overseas factors, I believe that now is a prime opportunity to raise the policy interest rate."),
    ("takata", "2025-10-20", "koen_2025/ko251020a.htm", "Speech at a meeting with business leaders", 0.5, SEP25, "hike to 0.75%",
     "With respect to the conduct of monetary policy, my view is that the Bank is still in the process of gradually shifting gears, based on the recognition that the \"true dawn\" is now in sight."),
    ("tamura", "2025-10-16", "koen_2025/ko251016a.htm", "Speech at a meeting with local leaders", 0.5, SEP25, "hike to 0.75%",
     "So far, the Bank has raised the policy interest rate to 0.5 percent, but my view is that the impact of the policy interest rate hikes on Japan's overall economy has been extremely limited. I believe that the policy interest rate is still far away from the neutral interest rate."),
    ("tamura", "2025-10-16", "koen_2025/ko251016a.htm", "Speech at a meeting with local leaders", 0.5, SEP25, "hike to 0.75%",
     "Given that there are currently both upside and downside risks, I do not believe that the Bank should immediately raise the policy interest rate to a restrictive level in an attempt to curb inflation."),
    ("ueda", "2025-12-01", "koen_2025/ko251201a.htm", "Speech at a meeting with business leaders", 0.5, OCT25, "hold",
     "At the MPM, the Bank will examine and discuss economic activity and prices at home and abroad as well as developments in financial and capital markets, including the point I just mentioned, based on various data and information, and will consider the pros and cons of raising the policy interest rate and make decisions as appropriate."),
]


def norm(s):
    return " ".join(s.split())


def context_line(rate, decision, vote):
    return (f"Policy rate {rate:g}%. Last decision: {decision}. "
            f"Market-implied path: not available. Speaker's last vote: {vote or 'none'}.")


def main():
    items = []
    for n, (member, doc_id, passage) in enumerate(BOE, 1):
        doc = json.loads((RAW / f"{doc_id}.json").read_text(encoding="utf-8"))
        assert norm(passage) in norm(doc["text"]), f"not verbatim: {doc_id}"
        assert doc["member_id"] == member
        ctx = build_context("BoE", member, doc["published"])
        name, role = NAMES[member]
        is_minutes = doc["kind"] == "minutes_statement"
        items.append({
            "id": f"v1b-boe-{n:02d}", "bank": "BoE", "speaker": name, "role": role,
            "date": doc["published"][:10],
            "source_type": "minutes_statement" if is_minutes else doc["source_type_hint"],
            "venue": f"{doc['published'][:7]} MPC minutes, written statement" if is_minutes else doc["title"],
            "context": context_line(ctx["policy_rate"], f"{ctx['last_decision']} on {ctx['last_decision_date']}",
                                    ctx["speaker_last_vote"]),
            "url": doc["url"], "text": passage, "document_id": doc_id,
        })
    for n, (member, date, path, venue, rate, decision, vote, passage) in enumerate(BOJ, 1):
        name, role = NAMES[member]
        items.append({
            "id": f"v1b-boj-{n:02d}", "bank": "BoJ", "speaker": name, "role": role, "date": date,
            "source_type": "speech", "venue": venue, "context": context_line(rate, decision, vote),
            "url": BOJ_URL + path, "text": passage,
        })
    OUT.write_text(json.dumps({
        "version": "blind_v1", "built": "2026-10-19", "rubric_under_test": "v1",
        "note": "Fresh holdout for rubric v1. Not used to build the rubric. Label blind; score blind.",
        "items": items,
    }, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(items)} statements written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
