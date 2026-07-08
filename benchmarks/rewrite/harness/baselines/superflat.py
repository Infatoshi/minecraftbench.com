"""Trivial baseline: vanilla default superflat (bedrock y0, dirt y1-2, grass y3, air above).

Usage: uv run --with numpy python superflat.py --seed S --cx0 A --cz0 B --cx1 C --cz1 D --out FILE
"""

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mcbd import CHUNK_U16, write_mcbd  # noqa: E402


def chunk() -> np.ndarray:
    c = np.zeros(CHUNK_U16, dtype=np.uint16)
    c[0:256] = 7 << 4            # bedrock, y=0
    c[256 : 3 * 256] = 3 << 4    # dirt, y=1..2
    c[3 * 256 : 4 * 256] = 2 << 4  # grass, y=3
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", required=True, type=int)
    ap.add_argument("--cx0", required=True, type=int)
    ap.add_argument("--cz0", required=True, type=int)
    ap.add_argument("--cx1", required=True, type=int)
    ap.add_argument("--cz1", required=True, type=int)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    n = (args.cx1 - args.cx0 + 1) * (args.cz1 - args.cz0 + 1)
    write_mcbd(args.out, args.seed, args.cx0, args.cz0, args.cx1, args.cz1, 0,
               np.tile(chunk(), n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
