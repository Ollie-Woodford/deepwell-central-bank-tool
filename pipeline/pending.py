"""
Documents waiting to be scored under the current rubric version, newest first.

    python -m pipeline.pending --limit 15
    python -m pipeline.pending --json      # machine-readable
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Optional

from .context import build_context, context_block
from .store import RAW, ROOT, SCORES, load_decisions


def rubric_version() -> str:
    m = re.search(r"^\*\*Version:\*\*\s*(\S+)", (ROOT / "rubric.md").read_text(encoding="utf-8"), re.M)
    if not m:
        raise ValueError("version line not found in rubric.md")
    return m.group(1)


def load_scores() -> list[dict]:
    out = []
    for f in sorted(SCORES.glob("[0-9]*.jsonl")):
        out += [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]
    return out


def pending(limit: Optional[int] = None, version: Optional[str] = None) -> list[dict]:
    version = version or rubric_version()
    scores = load_scores()
    done = {r.get("document_id") for r in scores if r.get("rubric_version") == version}
    docs = [json.loads(f.read_text(encoding="utf-8")) for f in RAW.glob("*/*.json")]
    docs = sorted((d for d in docs if d["id"] not in done), key=lambda d: d["published"], reverse=True)
    decisions = {}
    out = []
    for d in docs[:limit]:
        if d["bank"] not in decisions:
            decisions[d["bank"]] = load_decisions(d["bank"])
        ctx = build_context(d["bank"], d["member_id"], d["published"], decisions[d["bank"]])
        recent = [r for r in scores if r["member_id"] == d["member_id"] and r.get("key_quote")
                  and r["timestamp"] < d["published"]]
        recent = sorted(recent, key=lambda r: r["timestamp"])[-5:]
        out.append({
            "document_id": d["id"],
            "path": str((RAW / d["bank"].lower() / f"{d['id']}.json").relative_to(ROOT)),
            "member_id": d["member_id"],
            "published": d["published"],
            "source_type_hint": d["source_type_hint"],
            "title": d["title"],
            "text_chars": len(d["text"]),
            "context": ctx,
            "context_block": context_block(ctx),
            "recent_passages": [{"timestamp": r["timestamp"], "score": r["score"], "key_quote": r["key_quote"]}
                                for r in recent],
        })
    return out, len(docs)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    items, total = pending(args.limit)
    if args.json:
        print(json.dumps({"rubric_version": rubric_version(), "waiting": total, "items": items},
                         indent=1, ensure_ascii=False))
        return
    print(f"Rubric {rubric_version()}: {total} documents waiting, showing {len(items)}.\n")
    for it in items:
        print(f"== {it['document_id']}")
        print(f"   {it['path']}  ({it['text_chars']:,} chars, hint {it['source_type_hint']})")
        print(f"   {it['title']}")
        print("   " + it["context_block"].replace("\n", "\n   "))
        for r in it["recent_passages"]:
            print(f"   recent {r['timestamp'][:10]} {r['score']:+d}: {r['key_quote']}")
        print()


if __name__ == "__main__":
    main()
