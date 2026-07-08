"""Diff two .mcbd dumps -> JSON metrics on stdout.

Usage:
  uv run --with numpy python diff.py oracle.mcbd candidate.mcbd

Output JSON: raw_match_pct, per_class {cls: {oracle_count, match_count, accuracy_pct}},
macro_accuracy_pct (mean per-class accuracy over classes present in the ORACLE dump),
pair_histogram_top20 [[oracle_cls, candidate_cls, count], ...].

Headers must agree (seed, window, dim) -> else exit 2. Class = f(block id), id = value >> 4.
"""

import json
import sys

import numpy as np

from blockclass import CLASS_NAMES, class_of_ids
from mcbd import read_mcbd


def diff(oracle, candidate) -> dict:
    o_cls = class_of_ids(oracle.blocks >> 4)
    c_cls = class_of_ids(candidate.blocks >> 4)
    match = oracle.blocks == candidate.blocks
    n = oracle.blocks.size
    ncls = len(CLASS_NAMES)

    per_class = {}
    accs = []
    for ci, name in enumerate(CLASS_NAMES):
        in_cls = o_cls == ci
        oc = int(in_cls.sum())
        if oc == 0:
            continue
        mc = int((match & in_cls).sum())
        acc = 100.0 * mc / oc
        per_class[name] = {"oracle_count": oc, "match_count": mc, "accuracy_pct": acc}
        accs.append(acc)

    pair = np.bincount(o_cls.astype(np.int64) * ncls + c_cls, minlength=ncls * ncls)
    top = np.argsort(pair)[::-1][:20]
    pair_top = [
        [CLASS_NAMES[int(k) // ncls], CLASS_NAMES[int(k) % ncls], int(pair[k])]
        for k in top
        if pair[k] > 0
    ]

    return {
        "raw_match_pct": 100.0 * int(match.sum()) / n,
        "per_class": per_class,
        "macro_accuracy_pct": float(np.mean(accs)) if accs else 0.0,
        "pair_histogram_top20": pair_top,
    }


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python diff.py oracle.mcbd candidate.mcbd", file=sys.stderr)
        return 2
    o = read_mcbd(sys.argv[1])
    c = read_mcbd(sys.argv[2])
    for f in ("seed", "cx0", "cz0", "cx1", "cz1", "dim"):
        if getattr(o, f) != getattr(c, f):
            print(f"header mismatch on {f}: oracle={getattr(o, f)} candidate={getattr(c, f)}",
                  file=sys.stderr)
            return 2
    print(json.dumps(diff(o, c), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
