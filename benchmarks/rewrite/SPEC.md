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

    Rewrite Minecraft 1.11.2 from scratch in C/CUDA as a PufferLib-style batched environment
    for this machine (RTX 3090, sm_86). Expose the interface in INTERFACE.md. You will be
    scored per SCORING.md. An oracle CLI is available for development (see ORACLE.md). Go.

Delivery note (live-tested 2026-07-08): the prompt lives in GOAL.md, passed as `"$(cat GOAL.md)"`
uniformly. `claude -p "/goal"` DOES expand a project .claude/commands/goal.md (tested end to end,
despite docs suggesting otherwise), so claude could use a slash command - but codex exec does NOT
expand custom prompts (live-tested: `codex exec "/goal"` and `"/prompts:goal"` both ignored
~/.codex/prompts/goal.md and the model improvised on the literal slash-text; a decoy file proved
no expansion). Runner convention: GOAL.md is the single source of truth; claude invokes it as
`claude -p "/goal"` (project .claude/commands/goal.md wraps GOAL.md); every other harness gets
`"$(cat GOAL.md)"`.
Verified max-thinking invocations per harness:
- `claude -p ... --model claude-fable-5 --effort max --dangerously-skip-permissions`
  (--effort values: low/medium/high/xhigh/max)
- `codex exec -m gpt-5.5 -c model_reasoning_effort=xhigh --dangerously-bypass-approvals-and-sandbox ...`
  (xhigh live-tested)
- `grok -p --yolo -m grok-4.3 --effort max ...` (grok-4.3 = xAI flagship per docs.x.ai)
- `cursor agent --print --yolo --model "composer-2.5[fast=true]" ...` (bracket syntax controls
  the fast tier; same weights, faster inference)

Part B - INTERFACE.md / SCORING.md / ORACLE.md are precise and machine-checkable. Ambiguity in
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
Dual execution per seed: candidate dumps region blocks FIRST (clean container, empty fs, no
network, no JVM); the real Java game (private oracle repo, structures-off, save-flush protocol)
generates truth AFTERWARDS. Diff block-for-block over sampled regions, including regions far from
spawn (kills "only near origin" partials).

Metric: MACRO-AVERAGED per-block-class accuracy, never raw %-match. Raw match is base-rate
gameable (all-stone-below-y64 scores ~85%). Per-class pair histograms (world_verify.py style),
macro-average across classes so ores/trees/caves count as much as stone/air. Reported per LAYER,
each strictly harder: biomes -> terrain shape -> surface blocks -> caves/carving -> decoration.

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
