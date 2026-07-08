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

## Render metric

Tick-locked frame capture from your renderer vs the pinned deterministic 1.11.2 client at the
same seed, pose, and tick. Per-channel pixel diff with published tolerances calibrated so that
the real client re-run against itself passes (~0.3/channel) and any visible divergence fails
(sabotage measures ~69/channel). Scored when the leg lands; until then rendering is unscored
but the task includes it.

## Integrity verification (all mechanical, run on every submission)

- Eval seeds postdate your freeze; the seed space is 2^64. There is no golden to memorize.
- The eval container has no network, no JVM, and an empty filesystem except your repo. Your
  binary cannot call, wrap, or read the real game.
- Your candidate dumps BEFORE the oracle generates on that host; oracle output never exists
  where your code runs.
- Throughput dumps are taken mid-run from the same env instances being timed (see above); a
  fast fake path and a slow honest path cannot coexist.
- Repo size and asset budgets are enforced; high-entropy blobs are flagged and a
  complexity-vs-runtime correlation check plus perturbed-tape retests catch baked lookups.
- The repo is scanned for embedded Java bytecode, jars, or vendored Minecraft source; any hit
  voids the run.
- Every run gets an audit annotation (clean / flagged) published with its trace; annotations
  never override the measured numbers.

## Composite

Leaderboard reports the per-layer worldgen grid, sim divergence, render diff, and gated SPS.
Weighting is published with the sweep; fidelity gates throughput, never the reverse.
