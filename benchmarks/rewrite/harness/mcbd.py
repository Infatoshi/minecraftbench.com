"""Read/write the canonical .mcbd block dump (see FORMAT.md).

Library:
  write_mcbd(path, seed, cx0, cz0, cx1, cz1, dim, blocks)   # blocks: u16 numpy array
  read_mcbd(path) -> Mcbd(seed, cx0, cz0, cx1, cz1, dim, blocks)

CLI:
  uv run --with numpy python mcbd.py info FILE
"""

import struct
import sys
from dataclasses import dataclass

import numpy as np

MAGIC = b"MCBDUMP1"
HEADER = struct.Struct("<8sQiiiiII")  # magic, seed, cx0, cz0, cx1, cz1, dim, reserved
CHUNK_U16 = 16 * 16 * 256


@dataclass
class Mcbd:
    seed: int
    cx0: int
    cz0: int
    cx1: int
    cz1: int
    dim: int
    blocks: np.ndarray  # u16, nchunks * 65536

    @property
    def nchunks(self) -> int:
        return (self.cx1 - self.cx0 + 1) * (self.cz1 - self.cz0 + 1)


def write_mcbd(path, seed, cx0, cz0, cx1, cz1, dim, blocks) -> None:
    if cx1 < cx0 or cz1 < cz0:
        raise ValueError(f"bad window: cx {cx0}..{cx1}, cz {cz0}..{cz1}")
    blocks = np.ascontiguousarray(blocks, dtype=np.uint16)
    nchunks = (cx1 - cx0 + 1) * (cz1 - cz0 + 1)
    if blocks.size != nchunks * CHUNK_U16:
        raise ValueError(f"expected {nchunks * CHUNK_U16} u16 values, got {blocks.size}")
    with open(path, "wb") as f:
        f.write(HEADER.pack(MAGIC, seed & 0xFFFFFFFFFFFFFFFF, cx0, cz0, cx1, cz1, dim, 0))
        f.write(blocks.astype("<u2").tobytes())


def read_mcbd(path) -> Mcbd:
    with open(path, "rb") as f:
        raw = f.read()
    if len(raw) < HEADER.size:
        raise ValueError(f"{path}: truncated header ({len(raw)} bytes)")
    magic, seed, cx0, cz0, cx1, cz1, dim, _ = HEADER.unpack_from(raw)
    if magic != MAGIC:
        raise ValueError(f"{path}: bad magic {magic!r}")
    if cx1 < cx0 or cz1 < cz0:
        raise ValueError(f"{path}: bad window: cx {cx0}..{cx1}, cz {cz0}..{cz1}")
    nchunks = (cx1 - cx0 + 1) * (cz1 - cz0 + 1)
    expected = HEADER.size + nchunks * CHUNK_U16 * 2
    if len(raw) != expected:
        raise ValueError(f"{path}: expected {expected} bytes, got {len(raw)}")
    blocks = np.frombuffer(raw, dtype="<u2", offset=HEADER.size).astype(np.uint16)
    return Mcbd(seed, cx0, cz0, cx1, cz1, dim, blocks)


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] != "info":
        print("usage: python mcbd.py info FILE", file=sys.stderr)
        return 2
    d = read_mcbd(sys.argv[2])
    print(f"seed={d.seed} window=cx {d.cx0}..{d.cx1}, cz {d.cz0}..{d.cz1} "
          f"dim={d.dim} chunks={d.nchunks} blocks={d.blocks.size}")
    ids = d.blocks >> 4
    counts = np.bincount(ids)
    top = np.argsort(counts)[::-1][:10]
    for bid in top:
        if counts[bid] == 0:
            break
        print(f"  id {bid:4d}: {counts[bid]:10d} ({100.0 * counts[bid] / ids.size:.3f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
