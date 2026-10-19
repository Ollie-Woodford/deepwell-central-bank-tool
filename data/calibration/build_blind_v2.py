"""
Fresh blind test set for rubric v2, built 19 Oct 2026.

BoE: one passage from each of the 16 written statements in the 2026 minutes
that neither the gold set nor blind_v1 used. BoJ: Ueda (3 Oct 2025) and Himino
(2 Sep 2025), speeches neither set used. Same method and checks as
build_blind_v1.py. BoJ context: 31 Jul 2025 hold at 0.5%, unanimous;
19 Sep 2025 hold at 0.5%, 7-2 (Takata and Tamura proposing 0.75%).

    python data/calibration/build_blind_v2.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_blind_v1 import NAMES, RAW, ROOT, context_line, norm  # noqa: E402
from pipeline.context import build_context  # noqa: E402

OUT = ROOT / "data" / "calibration" / "blind_v2_statements.json"

BOE = [
    ("bailey", "boe-minutes-2026-02-05-bailey",
     "I therefore see scope for some further easing of policy. This does not mean that I expect to cut Bank Rate at any particular meeting."),
    ("lombardelli", "boe-minutes-2026-02-05-lombardelli",
     "Taken together, I prefer to hold Bank Rate at its current level. I am more concerned about the costs of cutting rates too quickly than too slowly, including the risks to credibility from any potential policy reversal that is not in response to a new shock."),
    ("mann", "boe-minutes-2026-02-05-mann",
     "A cut now would overweight the importance of the near-term mechanical disinflation and risk higher term premia."),
    ("ramsden", "boe-minutes-2026-02-05-ramsden",
     "However, with my starting point for an estimate of the neutral rate of around 3%, I judge that policy should be less restrictive in order to meet the 2% target sustainably in the medium term."),
    ("taylor", "boe-minutes-2026-02-05-taylor",
     "If we expect to be at or below the target with significant slack emerging in about six months, a neutral rate of 3% should be in our sights now."),
    ("bailey", "boe-minutes-2026-03-19-bailey",
     "Monetary policy must, however, respond to the risk of a more persistent effect on UK CPI inflation."),
    ("breeden", "boe-minutes-2026-03-19-breeden",
     "Absent this shock, the underlying disinflation process had continued broadly as I expected and, consistent with my vote in February, I would have expected to vote for a cut again in March."),
    ("dhingra", "boe-minutes-2026-03-19-dhingra",
     "If we see something resembling the lower-inflation scenario, I would expect to reduce Bank Rate, possibly quickly, over the rest of the year."),
    ("greene", "boe-minutes-2026-03-19-greene",
     "The risk of inflation persistence has risen, perhaps significantly, in light of the negative supply shock from the war in the Middle East."),
    ("lombardelli", "boe-minutes-2026-06-18-lombardelli",
     "Were signals to indicate inflation would persist above target, this would require policy to respond more forcefully to inflationary pressures."),
    ("mann", "boe-minutes-2026-06-18-mann",
     "Research shows that a forceful Bank Rate decision can have a quick effect on inflation and inflation expectations. So I have time to continue to evaluate measures of inflation expectations and financial restrictiveness to determine whether firms’ pricing and 2027 wage negotiations are on a target-consistent path for the medium term."),
    ("ramsden", "boe-minutes-2026-06-18-ramsden",
     "Holding Bank Rate at this meeting keeps options open as we continue to learn more about the path of the conflict. My reaction function will remain state-contingent on both the development of the conflict, and what that means for the outlook for the economy."),
    ("breeden", "boe-minutes-2026-07-30-breeden",
     "Financial conditions facing households and businesses have tightened materially since the onset of the conflict, and consistent with the baseline, provide sufficient restrictiveness for now."),
    ("dhingra", "boe-minutes-2026-07-30-dhingra",
     "An increase in Bank Rate now would be disproportionate as, unlike 2022, the starting point for this shock is much softer and the policy stance is more restrictive."),
    ("greene", "boe-minutes-2026-07-30-greene",
     "Unsurprisingly, there has been scant evidence of second-round effects, but I expect some to emerge."),
    ("pill", "boe-minutes-2026-07-30-pill",
     "The profound uncertainty surrounding the energy price outlook is likely to be prolonged and of unknown duration, rendering efforts to fine-tune the economy with monetary policy hazardous."),
]

BOJ_URL = "https://www.boj.or.jp/en/about/press/koen_2025/"
JUL25 = "hold, unanimous on 2025-07-31"
SEP25 = "hold, 7-2 (2 for a hike) on 2025-09-19"
BOJ = [
    ("ueda", "2025-10-03", "ko251003a.htm", "Speech at a meeting with business leaders", 0.5, SEP25, "hold",
     "Given these factors, it is important, first of all, to maintain accommodative financial conditions and thereby firmly support economic activity."),
    ("ueda", "2025-10-03", "ko251003a.htm", "Speech at a meeting with business leaders", 0.5, SEP25, "hold",
     "The Bank will carefully examine the likelihood that the baseline scenario for economic activity and prices will be realized, as well as both upside and downside risks, and will make monetary policy decisions as appropriate and without any preconceptions."),
    ("himino", "2025-09-02", "ko250902a.htm", "Speech at a meeting with local leaders", 0.5, JUL25, "hold",
     "Therefore, if the baseline scenario described earlier is realized, it would be appropriate for the Bank to continue, in accordance with improvement in economic activity and prices, to raise the policy interest rate and adjust the degree of monetary accommodation (Chart 9)."),
    ("himino", "2025-09-02", "ko250902a.htm", "Speech at a meeting with local leaders", 0.5, JUL25, "hold",
     "To date, we have not seen clear signs of such effects, but we cannot exclude the possibility that they could emerge in time."),
]


def main():
    used = set()
    for f in ("blind_v1_statements.json",):
        used |= {i["text"] for i in json.loads((OUT.parent / f).read_text())["items"]}
    gold = json.loads((OUT.parent / "gold_set_v1.json").read_text())["rows"]
    used |= {r["text"] for r in gold}

    items = []
    for n, (member, doc_id, passage) in enumerate(BOE, 1):
        doc = json.loads((RAW / f"{doc_id}.json").read_text(encoding="utf-8"))
        assert norm(passage) in norm(doc["text"]), f"not verbatim: {doc_id}"
        assert doc["member_id"] == member and passage not in used
        ctx = build_context("BoE", member, doc["published"])
        name, role = NAMES[member]
        items.append({
            "id": f"v2b-boe-{n:02d}", "bank": "BoE", "speaker": name, "role": role,
            "date": doc["published"][:10], "source_type": "minutes_statement",
            "venue": f"{doc['published'][:7]} MPC minutes, written statement",
            "context": context_line(ctx["policy_rate"], f"{ctx['last_decision']} on {ctx['last_decision_date']}",
                                    ctx["speaker_last_vote"]),
            "url": doc["url"], "text": passage, "document_id": doc_id,
        })
    for n, (member, date, page, venue, rate, decision, vote, passage) in enumerate(BOJ, 1):
        name, role = NAMES[member]
        items.append({
            "id": f"v2b-boj-{n:02d}", "bank": "BoJ", "speaker": name, "role": role, "date": date,
            "source_type": "speech", "venue": venue, "context": context_line(rate, decision, vote),
            "url": BOJ_URL + page, "text": passage,
        })
    OUT.write_text(json.dumps({
        "version": "blind_v2", "built": "2026-10-19", "rubric_under_test": "v2",
        "note": "Fresh holdout for rubric v2. Not used to build the rubric. Label blind; score blind.",
        "items": items,
    }, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(items)} statements written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
