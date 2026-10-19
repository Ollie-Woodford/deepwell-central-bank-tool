"""
Collect Ollie's Calibration Lab labels into one file for eval/compare.py.

The lab stores one document per label in its "labels" collection. Export them
with the ArtifactData tool (action "list", collection "labels", out_dir set to
a scratch folder), then:

    python -m eval.labels_from_lab <out_dir>/labels --prefix v1b- > data/calibration/blind_v1_labels.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path, help="folder of exported label JSON files")
    ap.add_argument("--prefix", default="", help="keep only statement ids starting with this")
    args = ap.parse_args(argv)
    rows = []
    for f in sorted(args.folder.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        d = d.get("data", d)
        sid = d.get("statement_id") or f.stem
        if sid.startswith(args.prefix):
            rows.append({"statement_id": sid, "score": d.get("score"), "flag": d.get("flag"),
                         "note": d.get("note")})
    print(json.dumps(rows, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
