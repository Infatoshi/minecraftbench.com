# Canonical block dump format (mcbd v1)

The single interchange format between candidates, the oracle wrapper, and the diff tool.
Everything in the worldgen-fidelity leg produces or consumes this.

## File: `<name>.mcbd`

Little-endian binary:

```
offset  size  field
0       8     magic "MCBDUMP1"
8       8     u64 seed
16      4     i32 cx0   (chunk x, inclusive)
20      4     i32 cz0   (chunk z, inclusive)
24      4     i32 cx1   (chunk x, inclusive; cx1 >= cx0)
28      4     i32 cz1   (chunk z, inclusive; cz1 >= cz0)
32      4     u32 dim   (0 = overworld; nether/end reserved)
36      4     u32 reserved (0)
40      ...   u16 blocks[]
```

`blocks[]` layout: chunk-major, row-major within the region -
for cz in cz0..cz1: for cx in cx0..cx1: one chunk record.
Chunk record: 16*16*256 u16 values, index = (y * 16 + z) * 16 + x
(x, z local 0..15, y 0..255). Value = (blockId << 4) | meta, vanilla 1.11.2 ids.
Air = 0. Total size = 40 + nchunks * 131072 bytes.

## Block classes (for per-class macro accuracy)

The diff tool groups block ids into classes; macro accuracy averages over classes present in
the ORACLE dump (candidate-only classes count as errors in their true class):

- air (0), stone-family (1,3 dirt is NOT here), dirt/grass (2,3), sand/gravel (12,13),
  water (8,9), lava (10,11), ores (14,15,16,21,56,73,74,129), wood (17,162),
  leaves (18,161), vegetation (31,32,37,38,39,40,81,83,86,103,106,110,111,141,142,175),
  snow/ice (78,79,80,174), clay/terracotta (82,159,172), bedrock (7),
  structure-ish (mossy 48, obsidian 49, spawner 52, chest 54, web 30, rails 66, planks 5,
  fences 85,113, torch 50, bone 216), other (everything else).

Class table lives in `blockclass.py` as the single source of truth; this list is informative.

## Tools (this directory)

- `mcbd.py`     - read/write library + `python mcbd.py info <file>` CLI.
- `mca2mcbd.py` - real-game region: parse .mca anvil region files -> .mcbd for a chunk window.
- `diff.py`     - `python diff.py oracle.mcbd candidate.mcbd` -> JSON metrics:
                  raw match %, per-class pair histogram, per-class accuracy, macro accuracy,
                  per-layer slices (biomes/terrain/surface/caves/decoration TBD v2).
- `baselines/`  - trivial candidates (all-stone, superflat) emitting .mcbd, to calibrate the
                  metric floor.
