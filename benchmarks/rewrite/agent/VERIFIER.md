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

## Trajectory metric (sim + render, one recording)

An action tape (see SPEC: tape format) is replayed through the real game and through your env
at the same post-freeze time-seed. Tapes are self-contained system tours - dig a pit, pour
water into it, pillar up and step off, place sand over a hole, let time pass - so every
segment probes a specific mechanic with a sharp consequence (fall damage starts at exactly 4
blocks; flat-ground water spreads exactly 7; a dug block drops on a specific tick). At every
keyframe (every 20 ticks) both sides emit state + local world dump + frame.

Scores, per tape:
- FIRST-DIVERGENCE TICK: the last keyframe at which your state and blocks still match
  reality. A stub that never moves diverges at the first keyframe.
- STATE MATCH: per-field and per-segment match rates across the whole tape (pose, vitals,
  block edits, fluid cells). Partial credit is real: correct movement scores the movement
  segments even if water is wrong. Fields you do not simulate must be reported honestly
  (your obs struct is the claim).
- PIXEL TIERS: per-channel frame diff at three published tolerances - strict (calibrated so
  the real client re-run against itself passes, ~0.3/channel), loose, structural. Sabotage
  measures ~69/channel, so the strict window is ~240x. Renderer quality climbs the tiers;
  it never gates the state scores.

Each graded run also produces a side-by-side video (oracle vs your env, divergence marked)
from the per-tick video/ frames, encoded at 20fps so playback is real time; videos are
display-only and never scored themselves.

## Throughput metric (fidelity-gated, same-instance)

`./mcbench --sps` style batched stepping, N envs, fixed wall window, on this machine's RTX
3090. MID-RUN, the verifier freezes random envs from the running batch and calls
mcb_dump_world / mcb_obs on those same instances; the dumps are diffed against the oracle.
Throughput counts ONLY if the mid-run dumps pass. A fast path that fakes stepping and a slow
path that renders dumps honestly will be caught by construction.

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

Leaderboard reports the per-layer worldgen grid, the trajectory scores (first-divergence,
state match, pixel tiers), and gated SPS.
Weighting is published with the sweep; fidelity gates throughput, never the reverse.
