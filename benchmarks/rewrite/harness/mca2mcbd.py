"""Convert real-game 1.11.2 anvil region files (.mca) to canonical .mcbd dumps.

Unlike the private repo's world_diff.read_mca_chunk (which discards metadata), this reader
keeps the Data nibble so the dump is faithful (id<<4)|meta per FORMAT.md.

Usage:
  uv run --with numpy --with nbt python mca2mcbd.py \
      --region /path/to/saves/qrl_SEED/region --seed SEED \
      --cx0 -8 --cz0 -8 --cx1 7 --cz1 7 --out oracle.mcbd

1.11.2 chunk NBT: Level.Sections[] each with Y (0..15), Blocks (4096 bytes),
optional Add (2048 nibble bytes, high id bits), Data (2048 nibble bytes, meta).
Section index i = y*256 + z*16 + x (YZX) which equals mcbd's (y*16+z)*16+x layout,
so sections copy straight in at y-offset Y*16.
"""

import argparse
import sys

import numpy as np
from nbt.region import RegionFile

from mcbd import write_mcbd

CHUNK_U16 = 16 * 16 * 256


def _nibbles(raw: bytes) -> np.ndarray:
    """2048 packed nibble bytes -> 4096 values (even index = low nibble)."""
    b = np.frombuffer(raw, dtype=np.uint8)
    out = np.empty(b.size * 2, dtype=np.uint16)
    out[0::2] = b & 0x0F
    out[1::2] = b >> 4
    return out


def read_chunk_u16(region_dir: str, cx: int, cz: int) -> np.ndarray:
    """One chunk -> u16[65536] in mcbd order, (id<<4)|meta. Missing chunk -> raises."""
    rx, rz = cx >> 5, cz >> 5
    rf = RegionFile(f"{region_dir}/r.{rx}.{rz}.mca")
    nbt_chunk = rf.get_nbt(cx & 31, cz & 31)
    if nbt_chunk is None:
        raise FileNotFoundError(f"chunk {cx},{cz} not present in r.{rx}.{rz}.mca")
    level = nbt_chunk["Level"]
    out = np.zeros(CHUNK_U16, dtype=np.uint16)
    for sec in level["Sections"]:
        y0 = sec["Y"].value * 16 * 256
        blocks = np.frombuffer(bytes(sec["Blocks"].value), dtype=np.uint8).astype(np.uint16)
        if "Add" in sec:
            blocks = blocks | (_nibbles(bytes(sec["Add"].value)) << 8)
        meta = _nibbles(bytes(sec["Data"].value))
        out[y0 : y0 + 4096] = (blocks << 4) | meta
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", required=True)
    ap.add_argument("--seed", required=True, type=int)
    ap.add_argument("--cx0", required=True, type=int)
    ap.add_argument("--cz0", required=True, type=int)
    ap.add_argument("--cx1", required=True, type=int)
    ap.add_argument("--cz1", required=True, type=int)
    ap.add_argument("--dim", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    chunks = []
    for cz in range(args.cz0, args.cz1 + 1):
        for cx in range(args.cx0, args.cx1 + 1):
            chunks.append(read_chunk_u16(args.region, cx, cz))
    blocks = np.concatenate(chunks)
    write_mcbd(args.out, args.seed, args.cx0, args.cz0, args.cx1, args.cz1, args.dim, blocks)
    print(f"wrote {args.out}: {len(chunks)} chunks, seed {args.seed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
