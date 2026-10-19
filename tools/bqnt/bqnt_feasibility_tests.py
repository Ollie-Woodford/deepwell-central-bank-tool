# BQNT feasibility tests for the central bank hawk/dove dashboard
#
# How to use: open BQNT on the Terminal, start a new Python notebook, and
# paste each CELL below into its own notebook cell. Run with Shift+Enter.
# Every cell catches its own errors and prints PASS / FAIL / CHECK, so run
# all of them even if one fails. Copy the printed output back to Claude.
#
# Nothing here sends data outside the Terminal. Test 3 only checks whether
# outside websites can be reached; it sends no Bloomberg data and needs no
# API key.


# ============================================================================
# CELL 0: setup
# ============================================================================
import os, sys, datetime
print("Python", sys.version.split()[0])
print("Working folder:", os.getcwd())
print("Run at:", datetime.datetime.now().isoformat(timespec="seconds"))

try:
    import bql
    bq = bql.Service()
    print("PASS  BQL service started")
except Exception as e:
    bq = None
    print("FAIL  BQL could not start:", repr(e))


# ============================================================================
# CELL 1: market-implied rate path (the 'expected policy' baseline)
# ============================================================================
# OIS swap rates at several tenors approximate the market-implied path.
# The tickers below are best guesses. If any come back empty, find the right
# ones by typing "SONIA OIS" or "TONA OIS" into the Terminal search bar and
# replace them here.

OIS_TICKERS = {
    "GBP SONIA OIS": ["BPSWS1Z Curncy", "BPSWSC Curncy", "BPSWSF Curncy", "BPSWS1 Curncy", "BPSWS2 Curncy"],
    "JPY TONA OIS":  ["JYSO1Z Curncy", "JYSOC Curncy", "JYSOF Curncy", "JYSO1 Curncy", "JYSO2 Curncy"],
}
# Tenor guide: 1Z = 1 month, C = 3 months, F = 6 months, 1 = 1 year, 2 = 2 years

ois_results = {}
if bq is None:
    print("SKIP  BQL not available")
else:
    for curve, tickers in OIS_TICKERS.items():
        try:
            req = bql.Request(tickers, {"Last": bq.data.px_last()})
            df = bq.execute(req)[0].df()
            ois_results[curve] = df
            got = df["Last"].notna().sum()
            status = "PASS " if got == len(tickers) else "CHECK"
            print(f"{status} {curve}: {got}/{len(tickers)} tickers returned a price")
            print(df, "\n")
        except Exception as e:
            print(f"FAIL  {curve}:", repr(e))


# ============================================================================
# CELL 2: news access (can we get story text, or only headlines?)
# ============================================================================
# BQL is mainly for market data, so this is a discovery test: it looks for any
# news-related functions or packages available in this environment.

import pkgutil

if bq is not None:
    news_fields = [n for n in dir(bq.data) if "news" in n.lower() or "story" in n.lower()]
    print("BQL data items mentioning news/story:", news_fields or "none found")

    news_funcs = [n for n in dir(bq.func) if "news" in n.lower()]
    print("BQL functions mentioning news:", news_funcs or "none found")

modules = sorted(m.name for m in pkgutil.iter_modules()
                 if any(k in m.name.lower() for k in ("news", "bq", "blp", "bloomberg")))
print("Installed packages that may relate to Bloomberg or news:", modules or "none found")

print("\nCHECK  Also open the BQNT example notebooks / help (search 'news' there)")
print("       and note whether any example retrieves full story text.")


# ============================================================================
# CELL 3: outbound internet (can BQNT reach Claude and the bank websites?)
# ============================================================================
# This only checks reachability. No Bloomberg data is sent and no API key is
# used. Any HTTP response (even 401 or 404) means the site is reachable.

SITES = {
    "Anthropic API (for scoring)": "https://api.anthropic.com/v1/messages",
    "Bank of England":             "https://www.bankofengland.co.uk/",
    "Bank of Japan":               "https://www.boj.or.jp/en/",
    "BIS speeches":                "https://www.bis.org/cbspeeches/",
    "PyPI (installing packages)":  "https://pypi.org/simple/anthropic/",
}

try:
    import requests
    for name, url in SITES.items():
        try:
            r = requests.get(url, timeout=10)
            print(f"PASS  {name}: reachable (HTTP {r.status_code})")
        except Exception as e:
            print(f"FAIL  {name}: blocked or unreachable ({type(e).__name__})")
except ImportError:
    print("FAIL  'requests' package not available")

# Can packages be installed? (Some BQNT setups use an environment manager
# instead of pip; if this fails, look for 'Environments' or 'Packages' in the
# BQNT menus and try adding 'anthropic' there.)
try:
    import anthropic
    print("PASS  anthropic package already installed, version", anthropic.__version__)
except ImportError:
    print("CHECK anthropic package not installed. Try in a new cell:")
    print("      %pip install anthropic")


# ============================================================================
# CELL 4: export (can results leave BQNT as a file?)
# ============================================================================
import pandas as pd

try:
    if ois_results:
        out = pd.concat(ois_results, names=["curve"]).reset_index()
    else:
        out = pd.DataFrame({"test": ["export check"], "value": [1]})
    path = os.path.join(os.getcwd(), "bqnt_export_test.csv")
    out.to_csv(path, index=False)
    print("PASS  CSV written to:", path)
    print("CHECK Find it in the BQNT file browser and try downloading it")
    print("      to your computer. Note whether that works.")
except Exception as e:
    print("FAIL  Could not write CSV:", repr(e))


# ============================================================================
# CELL 5: summary to copy back
# ============================================================================
print("""
Copy everything printed above and paste it back, plus answers to:
  1. Did the CSV download to your computer?          yes / no
  2. Did any BQNT example show full news story text? yes / no / unsure
  3. Is this Terminal Montfleur's or a personal one?
""")
