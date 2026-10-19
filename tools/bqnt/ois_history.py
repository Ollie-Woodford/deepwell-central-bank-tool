"""
Weekly OIS history for the baseline, run inside BQNT.

Pulls the same SONIA and TONA OIS tickers as the weekly manual export
(docs/SOURCES.md, Market baseline) for every Friday in a date range, and
prints one CSV block per date in the format engine/baseline.py reads:

    curve,ID,DATE,CURRENCY,Last

Copy each block into data/baseline/ois_YYYY-MM-DD.csv (or the whole output
into one file and ask Claude to split it). Written on 19 Oct 2026 without
access to BQNT, so the BQL call has not been run yet: if it errors, the
likely fix is in the dates/frq arguments.
"""

import bql

START, END = "2024-10-01", "2026-10-16"

CURVES = {
    "GBP SONIA OIS": ["BPSWS1Z Curncy", "BPSWSC Curncy", "BPSWSF Curncy", "BPSWS1 Curncy", "BPSWS2 Curncy"],
    "JPY TONA OIS": ["JYSO1Z Curncy", "JYSOC Curncy", "JYSOF Curncy", "JYSO1 Curncy", "JYSO2 Curncy"],
}

bq = bql.Service()
rows = {}  # date -> list of csv lines
for curve, tickers in CURVES.items():
    item = bq.data.px_last(dates=bq.func.range(START, END), frq="W", fill="prev")
    df = bql.combined_df(bq.execute(bql.Request(tickers, {"Last": item})))
    df = df.reset_index()
    for _, r in df.iterrows():
        day = str(r["DATE"])[:10]
        rows.setdefault(day, []).append(f"{curve},{r['ID']},{day},,{r['Last']}")

for day in sorted(rows):
    print(f"### ois_{day}.csv")
    print("curve,ID,DATE,CURRENCY,Last")
    print("\n".join(rows[day]))
    print()
