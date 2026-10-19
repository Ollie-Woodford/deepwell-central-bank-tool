"""Starter calibration set: real, verbatim statements gathered 16 Oct 2026.

Quotes are exact wording from the source (some trimmed to a clause, marked
with '...'). Items typed news_speculation are reporters' paraphrases, not
quotes. Context describes policy at the time; it is not a score.
"""
import json

BOE_RATE = "Bank Rate 3.75% (unchanged since Dec 2025). Gulf conflict has pushed up energy prices."
U = {
    "pill_mar": "https://www.bankofengland.co.uk/speech/2026/march/huw-pill-speech-at-national-bank-of-the-republic-of-north-macedonia-and-suerf-conference",
    "pill_sep": "https://www.bankofengland.co.uk/speech/2026/september/remarks-at-the-edinburgh-chamber-of-commerce",
    "mins_sep": "https://www.bankofengland.co.uk/-/media/boe/files/monetary-policy-summary-and-minutes/2026/monetary-policy-summary-and-minutes-september-2026.pdf",
    "mins_apr": "https://www.morningstar.co.uk/uk/news/AN_1777550233450844600/update-boe-mpc-members-see-higher-rates-should-energy-shock-persist.aspx",
    "lomb_sep": "https://www.bankofengland.co.uk/speech/2026/september/clare-lombardelli-speech-at-the-sixth-biennial-conference-poland",
    "taylor_sep": "https://www.bankofengland.co.uk/speech/2026/september/searching-for-signposts-speech-by-alan-taylor",
    "taylor_jun": "https://www.bankofengland.co.uk/speech/2026/june/alan-taylor-speech-at-the-barclays-and-centre-for-economic-policy-research",
    "mann_oct": "https://www.bankofengland.co.uk/speech/2026/october/catherine-mann-nomura-investor-conference",
    "mann_jul": "https://www.bankofengland.co.uk/speech/2026/july/catherine-l-mann-fireside-chat-at-the-natixis-cib-conference-on-private-debt",
    "greene_jun": "https://www.bankofengland.co.uk/speech/2026/june/megan-greene-speech-at-university-of-derby-business-school",
    "bailey_may": "https://www.bankofengland.co.uk/speech/2026/may/andrew-bailey-speech-at-the-reykjavik-2026-economic-conference",
    "bailey_jul": "https://www.bankofengland.co.uk/-/media/boe/files/monetary-policy-report/2026/july/opening-remarks-july-2026.pdf",
    "ramsden_sep": "https://www.bankofengland.co.uk/speech/2026/september/dave-ramsden-speech-on-quantitative-tightening",
    "dhingra_jun": "https://www.newsquawk.com/headlines/boes-dhingra-says-it-is-very-hard-to-say-what-her-future-rate-decisions-will-be-it-depends-on-energy-prices",
    "boj": "https://www.boj.or.jp/en/about/press/koen_2026/",
    "boj_sep_vote": "https://investinglive.com/central-banks/yen-weakens-on-boj-hike-as-two-dissents-temper-hawkish-read-alt-headlines/",
    "boj_jun_soo": "https://www.nationthailand.com/news/40067838",
    "sato_oct": "https://www.thestar.com.my/business/business-news/2026/10/07/boj039s-dovish-dissenter-signals-support-for-future-rate-hikes",
    "sato_jun": "https://alfi.dev.theedgesingapore.com/news/japan/takaichis-central-bank-board-pick-signals-tame-view-inflation",
    "asada_jul": "https://www.newsquawk.com/headlines/bojs-asada-says-a-rate-hike-could-slow-the-economy",
    "uchida_jun": "https://english.adnkronos.com/2026/06/16/boj-to-continue-rate-hikes-deputy-gov-uchida/",
    "ueda_sep": "https://theedgemalaysia.com/node/818488",
}
def boj(page): return U["boj"] + page

ROLES = {
    "Andrew Bailey": "Governor", "Clare Lombardelli": "Deputy Governor, Monetary Policy",
    "Sarah Breeden": "Deputy Governor, Financial Stability", "Dave Ramsden": "Deputy Governor, Markets and Banking",
    "Huw Pill": "Chief Economist", "Catherine Mann": "External member", "Swati Dhingra": "External member",
    "Megan Greene": "External member", "Alan Taylor": "External member",
    "Kazuo Ueda": "Governor", "Shinichi Uchida": "Deputy Governor", "Ryozo Himino": "Deputy Governor",
    "Hajime Takata": "Policy Board member", "Naoki Tamura": "Policy Board member", "Junko Koeda": "Policy Board member",
    "Kazuyuki Masu": "Policy Board member", "Toichiro Asada": "Policy Board member", "Ayano Sato": "Policy Board member",
}

# (speaker, date, source_type, venue, context_extra, url, [quotes])
BOE = [
    ("Huw Pill", "2026-03-24", "speech", "SUERF conference, Skopje", "Week after a unanimous hold.", U["pill_mar"], [
        "the burden of proof lies on the side of those seeking to deny a role for structural change",
        "I see the upside risks to price stability mounting as a result of events in the Gulf.",
        "I stand ready to act – if necessary – to contain the lasting components of any new inflationary pressures",
        "The fog of uncertainty in which we always operate cannot be an excuse for inaction.",
        "...support the unanimous MPC decision to hold Bank Rate at 3¾% at our meeting last week.",
    ]),
    ("Huw Pill", "2026-09-03", "speech", "Edinburgh Chamber of Commerce", "Previous meeting (July): 6-3 hold, three voted to hike.", U["pill_sep"], [
        "my own response to this question has pointed to a need to raise Bank Rate to 4%",
        "In my view, in this environment we cannot wait for uncertainties to resolve themselves before acting.",
        "I am convinced that events in the Gulf have not triggered a de-anchoring of longer-term inflation expectations",
        "I do not draw much comfort from the relatively benign developments in prices, costs and wages",
        "Raising Bank Rate on this basis need not be the start of a prolonged and aggressive series of increases.",
    ]),
    ("Clare Lombardelli", "2026-09-24", "speech", "Biennial conference, Poland", "Previous meeting (Sept): 6-3 hold, she voted to hold.", U["lomb_sep"], [
        "The key judgement for monetary policy is whether emerging evidence suggests inflation may become persistent.",
        "policy is increasingly likely to need to tighten if elevated energy prices persist",
        "Current monetary and financial conditions are restrictive and are already leaning against inflationary pressures.",
        "We cannot offer firm guidance on the path of policy",
        "There is little in the data so far to suggest that second-round effects are large, but it is too soon to tell.",
        "But this is by no means suggesting that monetary policy should respond mechanically to movements in energy prices.",
    ]),
    ("Alan Taylor", "2026-06-23", "speech", "Barclays and CEPR conference", "", U["taylor_jun"], [
        "In my view, interest rates can and should resume their downward path to neutral in Scenario T.",
        "an extended hold at this level is, to me, very much the correct and appropriately measured policy response",
        "If the energy price path does not deviate markedly from the current benign market curves, I am doubtful.",
        "And a substantial and opposing tail risk remains.",
    ]),
    ("Alan Taylor", "2026-09-29", "speech", "Searching for signposts", "Previous meeting (Sept): 6-3 hold, he voted to hold.", U["taylor_sep"], [
        "the case for further rate increases is not compelling to me unless energy prices remain high for an extended period",
        "the current stance is more than sufficient to weigh on demand and inflation",
        "Nevertheless, there remains a nontrivial risk.",
        "The overall message is that energy risks into winter are two-sided but asymmetric.",
        "if pressure builds and second-round effects begin to gain traction, the policy assessment would have to change.",
    ]),
    ("Catherine Mann", "2026-07-02", "comment", "Fireside chat, Natixis CIB conference", "", U["mann_jul"], [
        "shifting my view towards a longer hold, and potentially a need to lean against that risk.",
        "Associated firm pricing reactions are also likely to keep inflation from moderating to the two percent target",
        "there was more upside risks to inflation compared to downside risks for activity.",
        "an activist move can bring inflation expectations and outcomes toward the two percent target.",
    ]),
    ("Catherine Mann", "2026-10-01", "speech", "Nomura investor conference", "Previous meeting (Sept): she voted to hike to 4%.", U["mann_oct"], [
        "In my view, our current monetary policy stance is not sufficiently tight",
        "At some point, we need to follow-through with Bank Rate rises",
        "the conflict in the Middle East has contributed to further upside risks to inflation",
        "raising Bank Rate to commit to the inflation target can help ensure a sustainable return of inflation",
        "Given rising upside risks to inflation, a risk management strategy to monetary policy is appropriate.",
    ]),
    ("Megan Greene", "2026-06-02", "speech", "University of Derby Business School", "", U["greene_jun"], [
        "I think the case for hiking rates grows as the conflict wears on",
        "a tightening in monetary policy over the next few weeks or months may be necessary",
        "A more credible strategy is to hike Bank Rate in Scenario M to lean against second-round effects.",
        "the risk of acting, even if inflation proves to be less persistent, is less severe than the risk of failing to act.",
    ]),
    ("Andrew Bailey", "2026-05-29", "speech", "Reykjavik Economic Conference", "", U["bailey_may"], [
        "While we are ready to adjust course as needed depending on how the situation evolves",
        "Monetary policy generally looks through the direct effects of energy prices on inflation.",
        "protracted indirect effects could keep inflation above target for too long unless monetary policy responds.",
        "But responding too early may generate undesirable volatility in output",
    ]),
    ("Andrew Bailey", "2026-07-30", "press_conference", "Monetary Policy Report press conference", "Decision that day: 6-3 hold, three voted to hike.", U["bailey_jul"], [
        "it is likely that we will have to tighten policy to counter inflationary pressures in the UK economy",
        "the paths would point to a looser policy stance than implied by the market curve",
        "We have to set policy now, seeing through the day-to-day volatility and weighing all the risks and uncertainties we face.",
    ]),
    ("Dave Ramsden", "2026-09-28", "speech", "Quantitative tightening: the next chapter", "Previous meeting (Sept): 6-3 hold, he voted to hold.", U["ramsden_sep"], [
        "I voted in the majority, as I have since the outbreak of the conflict in the Middle East to hold Bank Rate at 3.75%.",
        "I think the risks to the inflation outlook, whether external or domestically generated, have tilted more to the upside.",
        "were upside pressures on the inflation outlook to continue to build, there could be a case for increasing Bank Rate.",
    ]),
]
# Individual written statements in MPC minutes
MINUTES = [
    ("2026-04-30", "April MPC minutes", "Decision: 8-1 hold, one member voted to hike.", U["mins_apr"], [
        ("Andrew Bailey", "For now, the softer real economy makes it appropriate to maintain bank rate"),
        ("Sarah Breeden", "But if it were to materialise, I would stand ready to react, forcefully if necessary,"),
        ("Swati Dhingra", "there is a limit to how much output loss should be acceptable,"),
        ("Megan Greene", "We may end up with inflation somewhere between Scenarios B and C, necessitating a tighter stance,"),
        ("Clare Lombardelli", "would require policy to respond more forcefully to inflationary pressures."),
        ("Catherine Mann", "I would expect to increase bank rate so as to lean against inflation rising into 2027."),
        ("Dave Ramsden", "consider raising bank rate and accepting a larger output gap as a result,"),
        ("Alan Taylor", "This would entail a hold for some time, then a move to a neutral or accommodative stance,"),
        ("Huw Pill", "a prompt but modest hike in bank rate will help mitigate upside risks to price stability"),
    ]),
    ("2026-09-16", "September MPC minutes", "Decision: 6-3 hold; Greene, Mann and Pill voted to hike to 4%.", U["mins_sep"], [
        ("Andrew Bailey", "[If the conflict persists] it is likely that policy may have to tighten."),
        ("Sarah Breeden", "if risks to the outlook for second-round effects crystallise, it becomes increasingly appropriate for Bank Rate to respond."),
        ("Swati Dhingra", "I therefore continue to see value in waiting for a clearer read on the durable scale of the shock over the coming months."),
        ("Clare Lombardelli", "the case for raising Bank Rate is building the longer the conflict continues without lasting resolution."),
        ("Dave Ramsden", "there could be a case for increasing Bank Rate [if upside pressures keep building]"),
        ("Alan Taylor", "My view is that additional tightening is not warranted at present."),
        ("Catherine Mann", "Raising Bank Rate is a better risk-management strategy when faced with uncertainty about inflation dynamics."),
        ("Megan Greene", "Waiting for definitive evidence of second-round effects before acting would leave policy behind the curve."),
        ("Huw Pill", "Acting decisively now cuts through in a way that bolsters the clarity and effectiveness of policy choices."),
    ]),
]
BOE_OTHER = [
    ("Swati Dhingra", "2026-06-05", "news_speculation", "Newsquawk headline (paraphrase)", "", U["dhingra_jun"],
     "BoE's Dhingra says it is very hard to say what her future rate decisions will be, it depends on energy prices"),
]
for who in ["Huw Pill", "Megan Greene", "Catherine Mann"]:
    BOE_OTHER.append((who, "2026-09-16", "dissent_vote", "September MPC vote", "", U["mins_sep"],
                      "[Vote] Voted to raise Bank Rate by 0.25pp to 4%, against a 6-3 majority to hold at 3.75%."))

def boj_ctx(rate): return f"BoJ policy rate {rate}."
BOJ = [
    ("Naoki Tamura", "2026-02-13", "speech", "Kanagawa Keizai Doyukai", "0.75%", boj("ko260213a.htm"), [
        "my sense is that the neutral interest rate should be at least around 1 percent.",
        "my understanding is that there is still considerable distance to the neutral interest rate level",
        "even if the Bank raises its policy interest rate, financial conditions will remain accommodative.",
        "persistent inflation that cannot be described as moderate must also be avoided.",
    ]),
    ("Hajime Takata", "2026-02-26", "speech", "Local leaders, Kyoto", "0.75%", boj("ko260226a.htm"), [
        "I proposed that the Bank raise the policy interest rate to 1.0 percent as a further gear shift",
        "conduct further rate hikes in a gradual manner, rather than aiming to reach the expected neutral interest rate",
        "price increases now have a greater tendency to generate second-round effects",
        "it is necessary to bear in mind the risk that Japan might face greater-than-expected upswings in prices",
    ]),
    ("Ryozo Himino", "2026-03-02", "speech", "Local leaders, Wakayama", "0.75%", boj("ko260302a.htm"), [
        "it should gradually shift to a more neutral stance through moderate policy rate hikes.",
        "which would also argue for gradually raising the policy interest rate.",
        "the inflation gap remains slightly negative at present but is expected to approach zero in the future.",
        "the effects of the rise in food prices might take more time to subside than anticipated in the Outlook Report.",
        "I feel that asserting that the rate has reached 2 percent for certain may still be premature.",
    ]),
    ("Kazuyuki Masu", "2026-05-14", "speech", "Kagoshima Keizai Doyukai", "0.75%", boj("ko260514a.htm"), [
        "I am convinced that the Bank needs to raise the policy interest rate further,",
        "I believe it is desirable to raise the policy rate at the earliest stage possible.",
        "these factors may not be temporary shocks but rather represent more enduring trends",
    ]),
    ("Junko Koeda", "2026-05-21", "speech", "Local leaders, Fukuoka", "0.75%", boj("ko260521a.htm"), [
        "I therefore believe the Bank needs to continue to raise the policy interest rate",
        "It will therefore become even more important to proceed with interest rate normalization through policy interest rate hikes.",
        "risks to prices are skewed to the upside for both fiscal years",
        "I see some possibility that underlying inflation may exceed 2 percent looking ahead.",
    ]),
    ("Kazuo Ueda", "2026-06-03", "speech", "Kisaragi-kai, Tokyo", "0.75%", boj("ko260603a.htm"), [
        "the Bank will continue to raise the policy interest rate and adjust the degree of monetary accommodation",
        "I think the Bank will continue to raise the policy interest rate at an appropriate pace.",
        "should it be judged that upside risks to prices outweigh downside risks to economic activity",
        "the upside risks to prices appear to be greater overall and are likely to emerge sooner.",
        "it should be more vigilant about the risk of a significant upward deviation in inflation materializing",
    ]),
    ("Naoki Tamura", "2026-06-25", "speech", "Local leaders, Hyogo", "1.0% (raised 16 June)", boj("ko260625a.htm"), [
        "I believe it is important that, as early as now, the Bank move closer to a neutral monetary policy stance",
        "I expect upside risks when it comes to prices.",
        "...raising the policy interest rate by 0.25 percentage points at intervals of a few months",
        "I consider it necessary to accelerate the pace of rate hikes without hesitation",
        "the current policy interest rate is in an accommodative range, below the neutral interest rate.",
    ]),
    ("Ryozo Himino", "2026-08-27", "speech", "Local leaders, Saitama", "1.0%", boj("ko260827a.htm"), [
        "I believe the Bank should continue to raise the policy interest rate",
        "I would first like to stress that the rate hike is an adjustment in the degree of monetary accommodation, not a tightening.",
        "In particular, it is important to stabilize underlying inflation at a level around 2 percent.",
        "we should pay greater attention to the upside risk to prices than in the past.",
    ]),
    ("Hajime Takata", "2026-09-02", "speech", "Local leaders, Sapporo", "1.0%", boj("ko260902a.htm"), [
        "I believe, however, that 2026 represents a regime change where rate hikes will not be carried out at a fixed pace",
        "my view is that the Bank should not aim to reach the expected neutral interest rate,",
        "the Bank will need to adopt a nimble approach to address conditions at the time, including overseas developments.",
        "inflationary pressure reflecting the situation in the Middle East could push prices above the target.",
    ]),
    ("Kazuyuki Masu", "2026-09-10", "speech", "Local leaders, Fukui", "1.0%", boj("ko260910a.htm"), [
        "the negative real interest rate situation should be addressed as soon as possible",
        "there are concerns that the price hikes in these goods may not be temporary shocks",
        "what is most vital from now on is to ensure that the underlying inflation rate does not significantly exceed 2 percent.",
        "That said, financial conditions in Japan remain accommodative.",
        "If inflation accelerates here, there is a risk that the Bank might inevitably need to implement a rapid policy interest rate hike.",
    ]),
    ("Junko Koeda", "2026-10-15", "speech", "Local leaders, Kumamoto", "1.25% (raised 18 Sept)", boj("ko261015a.htm"), [
        "I believe that the Bank should adjust the policy interest rate in a timely manner",
        "the Bank should not become overly cautious about raising the policy interest rate.",
        "I believe that the level of the neutral interest rate is considerably above 1 percent",
        "Given that there have been considerable upside risks to prices",
        "I am paying more attention than before to the upside risks to prices",
    ]),
]
BOJ_OTHER = [
    ("Kazuo Ueda", "2026-09-18", "press_conference", "Post-meeting press conference", "1.25% (raised that day, 7-2)", U["ueda_sep"],
     "The stage for setting policy has changed."),
    ("Shinichi Uchida", "2026-06-16", "news_speculation", "Jiji report (paraphrase), standing in for Ueda", "1.0% (raised that day)", U["uchida_jun"],
     "[Paraphrase] Indicated the Bank would keep raising its policy rate, depending on economic and price developments."),
    ("Toichiro Asada", "2026-06-16", "dissent_vote", "June MPM vote", "Board raised rate from 0.75% to 1.0%", U["boj_jun_soo"],
     "[Vote] Voted against the hike to 1.0%. Summary of Opinions (attributed by press): should \"hold the rate steady at this point\"; a hike \"could suppress aggregate demand\"."),
    ("Toichiro Asada", "2026-07-07", "news_speculation", "Newsquawk headline (paraphrase)", "1.0%", U["asada_jul"],
     "BoJ's Asada says a rate hike could slow the economy"),
    ("Toichiro Asada", "2026-09-18", "dissent_vote", "September MPM vote", "Board raised rate from 1.0% to 1.25%, 7-2", U["boj_sep_vote"],
     "[Vote] Voted against the hike to 1.25%. Reasoning (paraphrase): core CPI growth still below 2% and the economy not clearly strong enough to justify a hike."),
    ("Ayano Sato", "2026-06-30", "news_speculation", "First press conference (paraphrase)", "1.0%", U["sato_jun"],
     "[Paraphrase] Said Japan's inflation views aren't very strong yet."),
    ("Ayano Sato", "2026-09-18", "dissent_vote", "September MPM vote", "Board raised rate from 1.0% to 1.25%, 7-2", U["boj_sep_vote"],
     "[Vote] Voted against the hike to 1.25%. Reasoning (paraphrase): economic and price developments have not substantially accelerated, so a hike was not appropriate."),
    ("Ayano Sato", "2026-10-07", "interview", "Kyodo interview", "1.25%", U["sato_oct"],
     "I support the idea that interest rates should be adjusted in stages, as current financial conditions are accommodative,"),
]

items = []
def add(bank, speaker, date, stype, venue, ctx, url, text):
    items.append({
        "id": f"{bank.lower()}-{len([i for i in items if i['bank']==bank])+1:03d}",
        "bank": bank, "speaker": speaker, "role": ROLES[speaker], "date": date,
        "source_type": stype, "venue": venue, "context": ctx, "url": url, "text": text,
    })

for sp, d, st, v, extra, url, qs in BOE:
    for q in qs: add("BoE", sp, d, st, v, (BOE_RATE + " " + extra).strip(), url, q)
for d, v, extra, url, pairs in MINUTES:
    for sp, q in pairs: add("BoE", sp, d, "minutes_statement", v, BOE_RATE + " " + extra, url, q)
for sp, d, st, v, extra, url, q in BOE_OTHER:
    add("BoE", sp, d, st, v, (BOE_RATE + " " + extra).strip(), url, q)
for sp, d, st, v, rate, url, qs in BOJ:
    for q in qs: add("BoJ", sp, d, st, v, boj_ctx(rate) + " Market expects further gradual hikes.", url, q)
for sp, d, st, v, rate, url, q in BOJ_OTHER:
    add("BoJ", sp, d, st, v, ("BoJ policy rate " + rate + ".") if "%" in rate and not rate.startswith("Board") else rate + ".", url, q)

assert not any("\u2014" in json.dumps(i, ensure_ascii=False) for i in items), "em dash found"
json.dump({"version": 1, "built": "2026-10-16", "items": items},
          open("/home/claude/calibration/statements_doc.json", "w"), ensure_ascii=False, indent=1)
from collections import Counter
print(len(items), Counter(i["bank"] for i in items), Counter(i["speaker"] for i in items).most_common())
