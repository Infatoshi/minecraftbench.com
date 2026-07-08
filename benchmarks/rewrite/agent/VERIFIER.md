# VERIFIER - how your submission is judged

Everything below is mechanical. There is no partial credit for effort, explanations, or code
quality; only what the verifier measures counts.

## Protocol: time-seed dual execution

Evaluation seeds are derived from the wallclock AFTER your run is frozen. For each eval seed:

1. The real Minecraft 1.11.2 (Java, structures off) generates the world on an air-gapped
   verifier host and the spawn-centered chunk window is recorded. Worldgen centers on the
   spawn point, which moves with the seed - windows are not fixed constants.
2. Your `./mcbench --dump-world` is then asked for that exact window, in a clean container:
   no network, no JVM, empty filesystem except your repo. It never sees oracle output.
3. Block-for-block diff in the canonical .mcbd format.

No golden exists before your run is frozen. There is nothing to memorize, embed, or look up.

## Worldgen metric

Per-block-class MACRO accuracy, not raw match. Blocks are grouped into classes (air, stone,
dirt/grass, sand/gravel, water, lava, ores, wood, leaves, vegetation, snow/ice, clay, bedrock,
structure-ish, other); accuracy is computed per class and averaged over classes present in the
oracle dump. Trivial fills score near zero: published baselines (all-stone, superflat) are run
alongside every sweep and the leaderboard shows skill above them. Reported per layer: biome
layout, terrain shape, surface, carving, decoration.

## Sim metric

Fixed action tapes (movement, digging, water, falls) replayed through the real game and your
env at the same seed. Per-tick state comparison (pose, vitals, block edits); metrics are
first-divergence tick and per-field match rates. Fields you do not simulate must be reported
honestly (your obs struct is the claim); a stub that never moves diverges at tick 1.

## Throughput metric (fidelity-gated, same-instance)

`./mcbench --sps` style batched stepping, N envs, fixed wall window, on this machine's RTX
3090. MID-RUN, the verifier freezes random envs from the running batch and calls
mcb_dump_world / mcb_obs on those same instances; the dumps are diffed against the oracle.
Throughput counts ONLY if the mid-run dumps pass. A fast path that fakes stepping and a slow
path that renders dumps honestly will be caught by construction.

## Composite

Leaderboard reports the per-layer worldgen grid, sim divergence, and gated SPS. Weighting is
published with the sweep; fidelity gates throughput, never the reverse.
