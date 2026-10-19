"""
Market-implied policy baseline from Bloomberg OIS exports.

Reads the CSV produced in BQNT (curve, ID, DATE, CURRENCY, Last), works out
each ticker's tenor, and converts the OIS rates into rough forward rates for
each window. Those forwards are the 'expected policy path' the rubric scores
against.

Approximation: simple interest, ACT/365, tenor averages rather than
meeting-dated OIS. Good enough for v1; replace with meeting-dated OIS once
access is confirmed.
"""

from __future__ import annotations

import csv
import io
import json
import sys
from dataclasses import dataclass, asdict

# Tenor in years, keyed by the ticker code between the curve root and " Curncy".
TENOR_CODES = {"1Z": 1 / 12, "C": 0.25, "F": 0.5, "1": 1.0, "2": 2.0}
CURVE_ROOTS = {"GBP SONIA OIS": ("BPSWS", "BoE"), "JPY TONA OIS": ("JYSO", "BoJ")}


@dataclass
class Window:
    start_years: float
    end_years: float
    forward_rate: float  # percent

    @property
    def label(self) -> str:
        def fmt(y):
            return f"{round(y * 12)}m" if y < 1 else f"{y:g}y"
        return f"{fmt(self.start_years)}-{fmt(self.end_years)}"


def tenor_of(ticker: str, root: str) -> float:
    code = ticker.replace(" Curncy", "").strip()
    if not code.startswith(root):
        raise ValueError(f"{ticker} does not belong to curve root {root}")
    suffix = code[len(root):]
    if suffix not in TENOR_CODES:
        raise ValueError(f"unknown tenor code '{suffix}' in {ticker}")
    return TENOR_CODES[suffix]


def parse_ois_csv(text: str) -> dict:
    """Return {bank: {'date': ..., 'points': [(tenor_years, rate_pct), ...]}}."""
    text = text.strip().strip("`").strip()
    rows = list(csv.DictReader(io.StringIO(text)))
    out: dict = {}
    for row in rows:
        curve = row["curve"].strip()
        if curve not in CURVE_ROOTS:
            raise ValueError(f"unknown curve '{curve}'")
        root, bank = CURVE_ROOTS[curve]
        entry = out.setdefault(bank, {"curve": curve, "date": row["DATE"], "points": []})
        if row["DATE"] != entry["date"]:
            raise ValueError(f"mixed dates in {curve}: {row['DATE']} vs {entry['date']}")
        entry["points"].append((tenor_of(row["ID"], root), float(row["Last"])))
    for entry in out.values():
        entry["points"].sort()
    return out


def implied_forwards(points: list[tuple[float, float]]) -> list[Window]:
    """Forward rate for each window between consecutive tenors."""
    windows = [Window(0.0, points[0][0], points[0][1])]
    for (t0, r0), (t1, r1) in zip(points, points[1:]):
        g0 = 1 + r0 / 100 * t0
        g1 = 1 + r1 / 100 * t1
        windows.append(Window(t0, t1, ((g1 / g0) - 1) / (t1 - t0) * 100))
    return windows


def build_baseline(text: str) -> dict:
    baseline = {}
    for bank, entry in parse_ois_csv(text).items():
        windows = implied_forwards(entry["points"])
        spot = windows[0].forward_rate
        baseline[bank] = {
            "as_of": entry["date"],
            "curve": entry["curve"],
            "windows": [
                {"window": w.label, "forward_rate": round(w.forward_rate, 3),
                 "change_vs_now_bp": round((w.forward_rate - spot) * 100)}
                for w in windows
            ],
            "priced_change_12m_bp": round(
                (next(w for w in windows if w.end_years == 1.0).forward_rate - spot) * 100
            ),
        }
    return baseline


if __name__ == "__main__":
    data = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    print(json.dumps(build_baseline(data), indent=2))
