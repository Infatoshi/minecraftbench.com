# MinecraftBench-Rewrite: SPEC

<!-- machine: anvil, path: ~/minecraftbench.com/benchmarks/rewrite -->

Status: planning. No harness code yet. This document is the design of record; DEVLOG.md records
decisions and dead ends as they happen.

## 1. The task

An autonomous LLM coding agent, given one prompt and a budget, must rewrite Minecraft 1.11.2 from
scratch in C/C++/CUDA (Rust allowed) as a highly parallel BATCHED environment - PufferLib-style
vectorized envs - targeting one pinned machine. It is scored on (a) fidelity against the real Java
game and (b) batched throughput. The deliverable is not a leaderboard trophy; a winning submission
is an actually usable RL training environment.

Working hypothesis, stated on the site: frontier models cannot do this end to end today. The bench
exists to measure the gradient of partial progress across model generations. Human existence proof
that the target is reachable: craftax.c hit 47.8M SPS from-scratch C; the private oracle repo got
worldgen to 99.69-99.98% block-exact vs real MC (with source access and weeks of tooling - the
agent gets neither).

## 2. Target system (declared per sweep, not fixed forever)

- Each sweep declares its target machine in results/ (hardware, driver, toolchain versions);
  scores are only comparable within a sweep. The prompt tells the agent what machine it is
  building for.
- First sweep target: anvil GPU1, RTX 3090 24GB (sm_86), Ryzen 9950X3D. Always `nvidia-smi`
  before sweeps (shared box; GPU0 is off-limits for eval runs).
- Portability beyond the declared target is not scored.

## 3. The prompt (two-part design)

Part A - the task prompt is deliberately short, vibe-coder style, version-pinned and published:

    rewrite minecraft 1.11.2 from scratch in C/CUDA as a batched RL env. spec in SPEC.md,
    verifier in VERIFIER.md. go.

Delivery note (live-tested 2026-07-08): the prompt lives in GOAL.md, passed as `"$(cat GOAL.md)"`
uniformly. `claude -p "/goal"` DOES expand a project .claude/commands/goal.md (tested end to end,
despite docs suggesting otherwise), so claude could use a slash command - but codex exec does NOT
expand custom prompts (live-tested: `codex exec "/goal"` and `"/prompts:goal"` both ignored
~/.codex/prompts/goal.md and the model improvised on the literal slash-text; a decoy file proved
no expansion). Runner convention: the prompt lives in a single `prompt.txt` (the only prompt file, ever) and
the runner passes its contents verbatim as the prompt argument to every harness. The site shows
the full prompt inline in each command so visitors see exactly what the models were told -
nothing hidden behind a filename. (Historical note, live-tested: `claude -p "/goal ..."` does
expand project slash commands; codex exec does not. Moot now - verbatim inline is the
convention.)
Verified max-thinking invocations per harness:
- `claude -p ... --model claude-fable-5 --effort max --dangerously-skip-permissions`
  (--effort values: low/medium/high/xhigh/max)
- `codex exec -m gpt-5.5 -c model_reasoning_effort=xhigh --dangerously-bypass-approvals-and-sandbox ...`
  (xhigh live-tested)
- `grok -p --yolo -m grok-4.3 --effort max ...` (grok-4.3 = xAI flagship per docs.x.ai)
- `cursor agent --print --yolo --model "composer-2.5[fast=true]" ...` (bracket syntax controls
  the fast tier; same weights, faster inference)

Part B - the agent-facing docs are precise and machine-checkable, named in field vocabulary:
SPEC.md (task spec: env ABI, action/obs layout, canonical dump format, dev-time oracle CLI) and
VERIFIER.md (verifier protocol: dual execution, per-class macro metrics, fidelity gates,
same-instance throughput gating). Ambiguity in
the contract produces disputes; hints about method (GenLayer, RNG order, meshing) contaminate the
measurement. NO anti-cheat language anywhere in the prompt: every guarantee is mechanical.

## 4. What the agent gets and does not get

GETS (in the sandbox):
- The interface contract (section 5), scoring rules (section 6), oracle CLI docs.
- Black-box oracle access at DEV time: `oracle dump-world --seed S --radius N`,
  `oracle replay-tape --seed S --tape T.json --dump-state`. Rate-limited, fully logged. Output is
  derived data (block grids, state CSVs) - publishable in traces.
- Toolchain: gcc/clang, nvcc (sm_86), make/cmake, standard libs. No JVM.

DOES NOT GET:
- Minecraft source in any form (decompiled or otherwise). Redistribution is illegal and any
  source quoted into the transcript would make traces unpublishable. The knowledge lives in the
  model's weights (cubiomes-era worldgen is thoroughly documented in the open).
- Network access.
- The eval harness code, thresholds, or diff tooling (rubric-leak prevention).
- Oracle access at EVAL time.

## 5. Interface contract (submission ABI)

The submission is a shared library + thin CLI, built by `make` at the repo root.

Vectorized env ABI (C, PufferLib-compatible):
- `mcb_make(int num_envs, uint64_t seed) -> handle`
- `mcb_reset(handle)`
- `mcb_step(handle, const McbAction* actions)` - action struct mirrors the qrl bridge:
  forward/back/left/right/jump/sneak/sprint/attack/use (0/1), hotbar 0-8, yaw/pitch deltas.
- Zero-copy observation buffers (pose, vitals, look, local voxel window; exact layout TBD).
- `mcb_dump_world(handle, int env_idx, int cx0, int cz0, int cx1, int cz1, u16* out)` - canonical
  block grid, `u16 = (blockId << 4) | meta`, vanilla 1.11.2 ids, chunk-major order.
- `mcb_dump_state(handle, int env_idx, McbState* out)` - pose, vitals, inventory, tick counter.

Convenience CLI (`./mcbench`): `--dump-world`, `--replay-tape`, `--sps --num-envs N`. The CLI is a
convenience for the agent's own iteration; it is NEVER the source of truth for scoring (see 7.2).

## 6. Scoring

Three legs. All fidelity legs run on TIME-SEEDS: `seed = hash(wallclock at eval start)`, drawn
after the submission is frozen. No golden exists before eval begins.

### 6.1 Worldgen fidelity (the massive cheap suite)
Dual execution per seed: the real Java game (private oracle repo, structures-off, save-flush
protocol) generates truth on an air-gapped host and the spawn-centered window is auto-discovered
from the save (pregen centers on SPAWN, which moves with the seed - windows are not constants;
measured on seed 489: core at cx -45..-21, cz 24..48). The candidate then dumps that exact window
in a clean container (empty fs, no network, no JVM - it can never see oracle output, and the seed
postdates submission freeze, so oracle-first loses nothing).

Metric: MACRO-AVERAGED per-block-class accuracy, never raw %-match. Raw match is base-rate
gameable - MEASURED on a real 441-chunk vanilla core (seed 489): all-stone raw 89.00% / macro
15.34%; superflat raw 74.99% / macro 9.55%. These baselines run alongside every sweep as the
published floor. Per-class pair histograms (world_verify.py style), macro-average across classes
so ores/trees/caves count as much as stone/air. Reported per LAYER, each strictly harder:
biomes -> terrain shape -> surface blocks -> caves/carving -> decoration.

Trivial baselines published with the bench: all-stone, superflat, biomes-only reference candidates.
Leaderboard shows skill above baseline, and the baselines' scores are printed on the site.

### 6.2 Sim fidelity (tick-trace)
Fixed action tapes replayed through the real game (qrl bridge, uncapped) and the candidate at the
same time-seed. Per-tick state diff (pose, vitals, block edits); metrics: first-divergence-tick +
per-field match rates. Tapes have checksummed consequences (dig, fluid flow, fall damage) so a
no-op sim visibly diverges. `null` = UNSIMULATED sentinel per field: unimplemented features are
reported as UNSIMULATED, never "matches zero" (false-pass guard).

### 6.3 Throughput (fidelity-gated, same-instance)
Batched SPS on the 3090 with N envs stepping real tapes. CRITICAL: mid-run, the harness freezes a
random subset of the batched envs and dumps world/state THROUGH THE ENV ABI of those same
instances, and diffs them. Throughput only counts if the mid-run dumps pass. This closes the
two-faced submission (accurate slow dump path + fast fake step path) and the stub-step exploit in
one mechanism. What is timed: steady-state step() throughput, resets amortized, fixed wallclock
window.

### 6.4 Composite
Leaderboard grid: per-layer worldgen scores, sim first-divergence + field rates, gated SPS. A
single headline number (weighting TBD) plus the full grid, kernelbench-hard style. Annotation lane
per cell: clean / leak / hack, with per-run YAML annotations.

## 7. Threat model (every countermeasure is mechanism, not prompt language)

| # | Attack | Countermeasure |
|---|--------|----------------|
| 1 | Base-rate gaming (all-stone scores high) | Macro-averaged per-class metric + published trivial baselines |
| 2 | Two-faced submission (slow-accurate dump, fast-fake step) | Fidelity dumps taken mid-throughput-run from the same env instances (6.3) |
| 3 | Stub step() infinite SPS | Same as 2, plus consequence-checksummed tapes |
| 4 | Memorized goldens | Time-seeds drawn after freeze; 2^64 seed space; no pre-existing goldens |
| 5 | Runtime oracle wrapping | Eval container: no JVM, no network, empty fs; throughput bar unreachable by the Java game (~881 TPS single-world uncapped) |
| 6 | Reading oracle saves on eval box | Ordering: candidate dumps BEFORE oracle generates; separate clean container |
| 7 | Harness/threshold tampering (rubric leak) | Agent sandbox never contains harness code; eval harness pinned at a commit hash chosen before runs |
| 8 | Overfitting published dev seeds | Dev seeds published, eval seeds are fresh time-seeds |
| 9 | Judge-model prompt injection in code/transcript | Judge checklist is mechanical (size budget, syscall audit, perturbed-tape retest, complexity-runtime correlation); judge writes annotations, never overrides numbers |
| 10 | Embedded mega-assets (baked lookup worlds) | Binary+asset size budget; complexity-vs-runtime correlation check; perturbed tape retest |

## 8. Oracle infrastructure (private; never in this repo)

Lives in `anvil:~/dev/minecraft/mc-1.11.2-env` (PRIVATE - bundles decompiled Mojang source, never
publish, never vendor here). What the bench uses from it:
- Headless deterministic Java game: pins already proven (chat hidden, Player0, clouds/fancy off,
  fixed time, cycles off) - two independent launches produced 0/921600 differing pixels.
- qrl bridge: tick-synced action replay, uncapped ~881 TPS, per-tick state obs.
- world_verify.py: block-for-block .mca region diff with per-class histograms.
- Gotcha protocol (hard-won): structures-off saves for RNG work; let save flush (no kill -9);
  fresh world folder per seed (stale level.dat); `pkill -f '[G]radleStart'` bracket-escape;
  standalone setsid launches over ssh.

This public repo ships only: harness client code, canonical dump format spec, derived goldens
(block grids, state CSVs, frames), baselines, results. Traces contain oracle OUTPUTS only.

## 9. Budget and run protocol

- Pinned per-run budget (tokens or wallclock; exact number TBD), published. "Models can't do it"
  is only meaningful relative to a budget; cross-model comparison collapses without pinning.
- ONE-SHOT IS CANONICAL (decided 2026-07-08): one prompt, one budget, no re-prompting or
  continue-nudges - stopping early is a measured long-horizon failure mode, not a confound,
  and nudge wording/cadence would be a free parameter models respond to differently. Budget
  is a ceiling; the verifier scores whatever is on disk at exit or cutoff. BUDGET UTILIZATION
  (wall-clock used / granted, from the run log) is a published leaderboard column so early
  stopping is visible mechanically. A steered continue-loop variant may exist later only as a
  clearly-labeled side experiment, never the benchmark.
- First eval target: GPT-5.5 via codex (Max plan credits). Then the usual roster.
- Harness: same runner pattern as kernelbench-hard sweeps (sandboxed agent, transcript capture,
  redaction pass, HF trace dataset per suite).

## 10. Later tiers (explicitly out of v0)

- Pixel-diff render leg: tick-locked frame capture vs the pinned deterministic client, sabotage-
  calibrated tolerances (native 0.289/ch vs sabotage 69.4/ch gives a ~240x separation window),
  fill-rule noise floor ~0.02% of pixels. v0 judges blocks and state only; render is where the
  private repo's craster/render-opt experience returns.
- Nether/end dims, mobs/AI depth, redstone: layer scoring extends naturally.

## 11. Open decisions

- [ ] Observation buffer layout (voxel window size, entity slots) - decide with PufferLib compat in mind
- [ ] Composite score weighting across the three legs
- [ ] Per-run budget number
- [ ] Tape corpus design (how many, what behaviors, who writes them)
- [ ] Oracle CLI rate limit for dev-time access
- [ ] Whether Rust submissions get the same ABI via cdylib (yes, probably; confirm)
