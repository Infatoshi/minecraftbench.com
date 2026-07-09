"""Score a candidate tape replay against the oracle recording -> JSON metrics on stdout.

Usage:
  uv run --with numpy --with pillow python traj_diff.py ORACLE_DIR CANDIDATE_DIR

Both dirs hold the keyframe artifacts of one tape replay (SPEC: tape format):
state_<t>.json, world_<t>.mcbd, frame_<t>.png; the oracle dir also has manifest.json
listing the keyframes. Grading rules (all published in agent/SPEC.md + VERIFIER.md):

- STATE: per-field exact equality per keyframe. `time.total_time` and `air` are excluded
  (wall-clock-coupled on the oracle side). A candidate field of null is the UNSIMULATED
  sentinel: it never matches, but it is tallied honestly instead of as a lie.
- BLOCKS: bitwise .mcbd equality after canonicalization - the check-decay meta bit (0x8)
  on leaves (ids 18, 161) is masked. Also reports the block match fraction.
- PIXELS: per-keyframe mean abs diff per channel, three published tiers. Thresholds are
  calibrated on the oracle's own cross-launch repro (tape mean 0.64, worst keyframe 13.9
  from camera interpolation on mid-motion frames; sabotage measures ~69):
  strict <= 16.0, loose <= 32.0, structural <= 48.0.
- FIRST DIVERGENCE: last keyframe tick with exact state AND blocks; -1 if none. Pixels
  never gate it.
"""

import json
import sys
from pathlib import Path

import numpy as np

from mcbd import read_mcbd

STATE_EXCLUDED_TOP = {"air"}
STATE_EXCLUDED_TIME = {"total_time"}
LEAF_IDS = (18, 161)
CHECK_DECAY_BIT = 0x8
PIXEL_TIERS = {"strict": 16.0, "loose": 32.0, "structural": 48.0}


def load_state(path):
    s = json.loads(Path(path).read_text())
    for k in STATE_EXCLUDED_TOP:
        s.pop(k, None)
    if isinstance(s.get("time"), dict):
        for k in STATE_EXCLUDED_TIME:
            s["time"].pop(k, None)
    return s


def flatten(obj, prefix=""):
    """Flatten nested dicts to dotted field paths; lists compare as single values."""
    if isinstance(obj, dict):
        out = {}
        for k, v in sorted(obj.items()):
            out.update(flatten(v, f"{prefix}{k}."))
        return out
    return {prefix.rstrip("."): obj}


def state_compare(oracle, cand):
    of, cf = flatten(oracle), flatten(cand)
    matched, unsimulated, mismatched = [], [], []
    for k, ov in of.items():
        cv = cf.get(k, None)
        if cv is None and ov is not None:
            unsimulated.append(k)
        elif cv == ov:
            matched.append(k)
        else:
            mismatched.append(k)
    total = len(of)
    return {
        "fields": total,
        "matched": len(matched),
        "unsimulated": len(unsimulated),
        "mismatched": mismatched[:20],
        "exact": len(matched) == total,
    }


def canon_blocks(d):
    v = d.blocks.copy()
    ids = v >> 4
    leaf = np.isin(ids, LEAF_IDS)
    v[leaf] &= np.uint16(~CHECK_DECAY_BIT & 0xFFFF)
    return v


def block_compare(opath, cpath):
    o, c = read_mcbd(opath), read_mcbd(cpath)
    if (o.cx0, o.cz0, o.cx1, o.cz1, o.dim) != (c.cx0, c.cz0, c.cx1, c.cz1, c.dim):
        return {"exact": False, "match_pct": 0.0, "error": "window mismatch"}
    ob, cb = canon_blocks(o), canon_blocks(c)
    eq = ob == cb
    return {"exact": bool(eq.all()), "match_pct": 100.0 * float(eq.mean())}


def pixel_compare(opath, cpath):
    from PIL import Image
    o = np.asarray(Image.open(opath).convert("RGB"), dtype=np.int16)
    c = np.asarray(Image.open(cpath).convert("RGB"), dtype=np.int16)
    if o.shape != c.shape:
        return {"mean_per_channel": None, "error": "size mismatch"}
    return {"mean_per_channel": float(np.abs(o - c).mean())}


def score(oracle_dir, cand_dir):
    oracle_dir, cand_dir = Path(oracle_dir), Path(cand_dir)
    manifest = json.loads((oracle_dir / "manifest.json").read_text())
    keyframes = manifest["keyframes"]
    ticks = manifest["ticks"]

    per_kf = []
    for t in keyframes:
        row = {"tick": t}
        co = cand_dir / f"state_{t}.json"
        if not co.exists():
            row.update(state={"exact": False, "error": "missing"},
                       blocks={"exact": False, "match_pct": 0.0, "error": "missing"},
                       pixels={"mean_per_channel": None, "error": "missing"})
            per_kf.append(row)
            continue
        row["state"] = state_compare(load_state(oracle_dir / f"state_{t}.json"),
                                     load_state(co))
        cw = cand_dir / f"world_{t}.mcbd"
        row["blocks"] = (block_compare(oracle_dir / f"world_{t}.mcbd", cw) if cw.exists()
                         else {"exact": False, "match_pct": 0.0, "error": "missing"})
        cf = cand_dir / f"frame_{t}.png"
        row["pixels"] = (pixel_compare(oracle_dir / f"frame_{t}.png", cf) if cf.exists()
                         else {"mean_per_channel": None, "error": "missing"})
        per_kf.append(row)

    last_match = -1
    for row in per_kf:
        if row["state"].get("exact") and row["blocks"]["exact"]:
            last_match = row["tick"]
        else:
            break

    n = len(per_kf)
    state_pct = 100.0 * sum(r["state"].get("matched", 0) / r["state"]["fields"]
                            for r in per_kf if r["state"].get("fields")) / n
    block_pct = sum(r["blocks"]["match_pct"] for r in per_kf) / n
    means = [r["pixels"]["mean_per_channel"] for r in per_kf
             if r["pixels"].get("mean_per_channel") is not None]
    tiers = {name: (100.0 * sum(m <= thr for m in means) / n)
             for name, thr in PIXEL_TIERS.items()}

    return {
        "keyframes": n,
        "ticks": ticks,
        "last_match_tick": last_match,
        "state_match_pct": round(state_pct, 2),
        "block_match_pct": round(block_pct, 2),
        "pixel_tape_mean": round(sum(means) / len(means), 3) if means else None,
        "pixel_tier_pct": {k: round(v, 1) for k, v in tiers.items()},
        "per_keyframe": per_kf,
    }


def main():
    if len(sys.argv) != 3:
        print("usage: python traj_diff.py ORACLE_DIR CANDIDATE_DIR", file=sys.stderr)
        return 2
    print(json.dumps(score(sys.argv[1], sys.argv[2]), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
