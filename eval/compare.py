"""
Compare the scorer with Ollie's labels.

    python -m eval.compare --labels data/calibration/blind_v1_labels.json \\
        --scores data/calibration/blind_v1_scores.json \\
        --statements data/calibration/blind_v1_statements.json > reports/blind_v1.md

labels:     [{"statement_id": ..., "score": int or null, "flag": null or str}, ...]
            (the Calibration Lab's labels collection)
scores:     [{"id": ..., "score": int or null, "flag": ..., "confidence": ..., "rationale": ...}, ...]
statements: {"items": [{"id", "bank", "speaker", "text", ...}, ...]}  (optional, for the report)

Reports exact match, within 1 point, average gap, bias (scorer minus Ollie;
positive means the scorer is more hawkish) and rank agreement (Spearman), on
statements both sides scored. Statements either side flagged are counted
separately.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Optional

TARGET_WITHIN_ONE = 0.85


def _ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1  # ties share the average rank
        i = j + 1
    return ranks


def spearman(a: list[float], b: list[float]) -> Optional[float]:
    if len(a) < 3:
        return None
    ra, rb = _ranks(a), _ranks(b)
    ma, mb = mean(ra), mean(rb)
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = sum((x - ma) ** 2 for x in ra) ** 0.5
    vb = sum((y - mb) ** 2 for y in rb) ** 0.5
    return cov / (va * vb) if va and vb else None


def metrics(pairs: list[tuple[int, int]]) -> dict:
    """pairs: (ollie, scorer)."""
    if not pairs:
        return {"n": 0}
    gaps = [s - o for o, s in pairs]
    return {
        "n": len(pairs),
        "exact": sum(g == 0 for g in gaps) / len(pairs),
        "within_1": sum(abs(g) <= 1 for g in gaps) / len(pairs),
        "average_gap": mean(abs(g) for g in gaps),
        "bias": mean(gaps),
        "rank_agreement": spearman([o for o, _ in pairs], [s for _, s in pairs]),
    }


def compare(labels: list[dict], scores: list[dict], statements: Optional[dict] = None) -> dict:
    lab = {l["statement_id"]: l for l in labels}
    sco = {s["id"]: s for s in scores}
    items = {i["id"]: i for i in (statements or {}).get("items", [])}
    common = sorted(set(lab) & set(sco))
    pairs, flagged, by_bank, rows = [], [], {}, []
    for sid in common:
        l, s = lab[sid], sco[sid]
        if l.get("flag") or s.get("flag") or l.get("score") is None or s.get("score") is None:
            flagged.append((sid, l.get("flag") or l.get("score"), s.get("flag") or s.get("score")))
            continue
        pairs.append((l["score"], s["score"]))
        bank = items.get(sid, {}).get("bank", sid.split("-")[0].upper())
        by_bank.setdefault(bank, []).append((l["score"], s["score"]))
        rows.append((sid, l["score"], s["score"], s.get("confidence"), s.get("rationale", "")))
    return {
        "overall": metrics(pairs),
        "by_bank": {b: metrics(p) for b, p in sorted(by_bank.items())},
        "flagged": flagged,
        "rows": rows,
        "missing_scores": sorted(set(lab) - set(sco)),
        "missing_labels": sorted(set(sco) - set(lab)),
        "items": items,
    }


def _fmt(m: dict) -> str:
    if not m.get("n"):
        return "| 0 | | | | | |"
    rank = f"{m['rank_agreement']:.2f}" if m["rank_agreement"] is not None else "n/a"
    return (f"| {m['n']} | {m['exact']:.0%} | {m['within_1']:.0%} | {m['average_gap']:.2f} "
            f"| {m['bias']:+.2f} | {rank} |")


def report(result: dict, title: str = "Blind test") -> str:
    o = result["overall"]
    verdict = ("meets" if o.get("n") and o["within_1"] >= TARGET_WITHIN_ONE else "misses")
    out = [f"# {title}", "",
           f"Target: at least {TARGET_WITHIN_ONE:.0%} within 1 point. Result: **{verdict}** the target.", "",
           "| | Statements | Exact | Within 1 | Average gap | Bias (scorer minus Ollie) | Rank agreement |",
           "|---|---|---|---|---|---|---|",
           "| All " + _fmt(o)]
    for b, m in result["by_bank"].items():
        out.append(f"| {b} " + _fmt(m))
    out += ["", "Positive bias means the scorer is more hawkish than Ollie.", ""]

    big = [r for r in result["rows"] if abs(r[2] - r[1]) >= 2]
    if big:
        out += ["## Gaps of 2 or more", "", "| Statement | Ollie | Scorer | Confidence | Text | Scorer's rationale |",
                "|---|---|---|---|---|---|"]
        for sid, o_, s_, conf, why in sorted(big, key=lambda r: -abs(r[2] - r[1])):
            it = result["items"].get(sid, {})
            text = it.get("text", "").replace("|", "/")
            who = it.get("speaker", "")
            out.append(f"| {sid} {who} | {o_:+d} | {s_:+d} | {conf if conf is not None else ''} "
                       f"| {text} | {why.replace('|', '/')} |")
        out.append("")
    if result["flagged"]:
        out += ["## Flagged by either side (not in the numbers)", ""]
        out += [f"- {sid}: Ollie {o_}, scorer {s_}" for sid, o_, s_ in result["flagged"]] + [""]
    if result["missing_scores"] or result["missing_labels"]:
        out += [f"Labelled but not scored: {', '.join(result['missing_scores']) or 'none'}. "
                f"Scored but not labelled: {', '.join(result['missing_labels']) or 'none'}.", ""]

    out += ["## All statements", "", "| Statement | Ollie | Scorer | Gap |", "|---|---|---|---|"]
    out += [f"| {sid} | {o_:+d} | {s_:+d} | {s_ - o_:+d} |" for sid, o_, s_, _, _ in result["rows"]]
    return "\n".join(out) + "\n"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", type=Path, required=True)
    ap.add_argument("--scores", type=Path, required=True)
    ap.add_argument("--statements", type=Path)
    ap.add_argument("--title", default="Blind test")
    args = ap.parse_args(argv)
    labels = json.loads(args.labels.read_text())
    labels = labels.get("rows", labels) if isinstance(labels, dict) else labels
    scores = json.loads(args.scores.read_text())
    statements = json.loads(args.statements.read_text()) if args.statements else None
    print(report(compare(labels, scores, statements), args.title), end="")


if __name__ == "__main__":
    main()
