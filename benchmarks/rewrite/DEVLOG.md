# DEVLOG - MinecraftBench-Rewrite

## 2026-07-07 - founding decisions (planning session)

- Task shape locked: one-prompt vibe-coder task ("rewrite MC 1.11.2 from scratch in C/CUDA,
  PufferLib-style, for this 3090") + precise machine-checkable interface/scoring appendices.
  No anti-cheat prompt language; all guarantees mechanical. See SPEC.md section 3/7.
- Rejected: model writes its own oracle (circular verification - the exact trap the private
  repo's gzip-CPU provisional goldens flag). Oracle = the real Java game, harness-owned, offline.
- Rejected: pre-frozen golden suites as the primary gate. Replaced with time-seed dual execution
  (seed = hash(wallclock) after submission freeze; candidate dumps first, oracle generates truth
  after). No golden exists before eval starts.
- Rejected: raw block %-match (base-rate gameable, all-stone scores ~85%). Macro-averaged
  per-class accuracy + published trivial baselines instead.
- Key anti-hack mechanism: throughput fidelity dumps taken MID-RUN from the same env instances
  producing the SPS number (closes two-faced submissions and stub step()).
- No MC source in the agent sandbox: legal (traces stay publishable) + purer measurement
  (knowledge from weights; cubiomes-era worldgen is public knowledge). Dev-time black-box
  oracle CLI instead, rate-limited and logged.
- v0 judges blocks + state only; pixel-diff render leg deferred (SPEC 10).
- First eval: GPT-5.5 via codex Max-plan credits.
- Site deployed (Vercel + Porkbun NS), placeholder leaderboard; monorepo mirrors kernelbench.com
  (site reads benchmarks/*/results/leaderboard.json at build time).

## 2026-07-08 - harness v1 measured on real data

- Diff toolchain live: mcbd.py / blockclass.py / diff.py / baselines / pytest suite (8 tests,
  exact == on ints). mca2mcbd.py verified earlier against the private repo's reader (100% id
  agreement, meta channel validated over 1005 chunks).
- Metric floor CALIBRATED on a real vanilla world (seed 489, 441-chunk decorated core):
  all-stone raw 89.00% / macro 15.34%; superflat raw 74.99% / macro 9.55%. The base-rate
  thesis is now a measurement, not an estimate - these are the published floors.
- Gotcha: pregen centers on SPAWN, not the origin (seed 489's core is cx -45..-21, cz 24..48).
  Eval windows cannot be fixed constants. mca2mcbd/oracle_gen now auto-discover the largest
  fully-populated chunk square (margin 2 for decoration completeness).
- Protocol consequence: the eval window is only known AFTER the oracle runs, so strict
  candidate-dumps-first ordering is dropped. New ordering: draw time-seed -> oracle generates
  (air-gapped) -> discover spawn window -> candidate dumps that window in the clean container.
  Integrity is unchanged: the seed still postdates submission freeze and the candidate
  container still has no network/JVM, so it can never see oracle output. Alternative
  (candidate must reimplement vanilla spawn selection to find the window itself) rejected as
  an unnecessary extra failure mode coupled to the metric.
- Codex delegate for the diff toolchain stalled 28 min with zero files written; killed and
  hand-wrote (~250 lines). Lesson: delegate scope was fine but always inspect output dir
  early, not just process liveness.
- End-to-end oracle cycle verified on fresh seed 20260708: launch -> qrl reset -> save flush ->
  .mca -> .mcbd in 34s total (pregen 6s once the JVM is warm-booted). A 20-seed eval suite is
  ~15 min of oracle time. Floor is seed-stable: all-stone macro 15.20% (vs 15.34% on 489).
- Run sandbox live (runner/SANDBOX.md): bare-metal `mcbench` unix user (GPU groups, 750 on
  /home/infatoshi, systemd scope caps 24 threads / 64G, CUDA_VISIBLE_DEVICES=1) - chosen over
  Docker for the run because the task targets real hardware (profilers, honest /proc) and
  run-time isolation is not eval integrity; the time-seed protocol is. Docker only for the
  eval-time dump (--network none). Smoke-tested e2e: codex ran as mcbench, built hello.c,
  collect.sh pulled bundle + tree + session transcripts; mcbench cannot read the private
  oracle repo.
- FIRST REAL RUN scored (20260708_031541, gpt-5.5 codex xhigh, mcbench sandbox). The model
  self-terminated at ~15 min of the 8h budget (codex exec is one-shot; budget is a ceiling,
  not a driver). Deliverables: full ABI + CLI + CUDA batched stepping, built clean in the
  air-gapped eval container, deterministic dumps, honest self-caveat that worldgen is an
  approximation. Scores over 2 post-freeze time-seeds: raw 85.9% / macro 18.3% vs all-stone
  floor raw 90.5% / macro 14.7%. The metric design paid off on run one: ALL-STONE BEATS
  GPT-5.5 ON RAW MATCH while macro correctly ranks them; ores/trees/water/caves ~0%.
  Self-reported 37.5M SPS left unverified (gating harness not yet built).
- Open question logged: should the runner re-prompt on early self-termination ("budget
  remains, continue") or is one-shot part of the measurement? Leaning: one-shot IS the
  benchmark - agents that stop early score what they shipped.
- What run one actually measured (contemplation): AMBITION CALIBRATION, not raw capability.
  The model knew precisely what the real task was (its own caveat names GenLayer and
  ChunkProvider) and declined to attempt it, self-imposing a "one pass" frame nothing in the
  prompt asked for - then treated pass-complete as done at 15 min of an 8h budget. Two
  distinct quantities to keep separate in analysis and eventually on the site:
    (a) unsteered judgment: given one prompt and a budget, does the agent decide to climb
        the real mountain? gpt-5.5 codex: no.
    (b) steered capability: with a human (or loop) saying "budget remains, keep going,"
        could it implement + verify seed-faithful worldgen? Plausibly - untested so far.
  The benchmark as designed scores (a); (b) is the follow-up experiment (continue-loop
  runner variant). Related failure: it barely used subagents - one early "compatibility
  notes" helper, no fan-out of GenLayer/carving/decoration as parallel workstreams, i.e. it
  never tried to warp its effective time budget through parallelism despite the prompt hint
  and 24 threads. Ambition calibration includes parallelism ambition.
- DECIDED: one-shot is canonical. No continue-loop, no re-prompting - stopping early is not
  a confound, it is the phenomenon (the bet is about end-to-end autonomy, and deciding to
  keep going is part of the task). A continue-loop would add a free parameter (nudge
  wording/cadence) that models respond to differently, trading a mechanical protocol for
  trust in nudge design - same reason anti-cheat prompt language is banned. Low scores are
  an asset (headroom is what keeps a benchmark alive; the oracle exists, so 100% is
  possible). Mitigation is reporting, not steering: BUDGET UTILIZATION becomes a published
  leaderboard column (wall-clock used vs granted, straight from the run log, zero design
  freedom) - "18.3% in 0.25h of 8h" tells the ambition-calibration story mechanically. A
  steered continue-loop variant may exist later only as a clearly-labeled side experiment,
  never the benchmark.
- Site stripped to kernelbench shape: terminal + one per-run table, nothing else. Schema v2
  is per-RUN records (kernelbench convention: a leaderboard is a run log, not a model
  ranking). Columns, in kernelbench's order logic (identity -> mechanical gates -> score ->
  cost -> judgment -> links): model | harness | date | built | worldgen | budget | audit |
  note | trace. Dropped for now: sortable headers and filters (kernelbench earned those at
  dozens of rows; add when row count justifies), tokens/cost columns (codex Max plan hides
  spend), per-layer detail (returns as an expandable or per-run page when layer slicing
  lands in diff.py v2). Baselines are muted rows in the same table so the floor sits next
  to the scores. Raw match lives in the worldgen cell's hover title - visible to the
  curious, not legitimizing the gameable number with its own column.
- Grading taxonomy fixed in SPEC 6.5: worldgen (biomes/terrain/surface/carving/decoration -
  same dumps, different masks, so per-category worldgen is free at eval time), sim
  (movement/falls/interaction/fluids/vitals/world-ticks - one tape each), performance
  (gated SPS), render deferred. Rule: a category unlocks on the leaderboard only when its
  mechanical measurement exists; nothing is ever scored by judgment. Terminal hero reordered:
  flags first, prompt last, all four harnesses.
- Eval-container parity bug caught by run two (kimi-k2.7-code): the dev host symlinks CUDA
  headers into /usr/local/include, so candidates build without -I flags; the eval image
  did not, failing honest builds. Fixed with CPATH/LIBRARY_PATH in eval/Dockerfile. Rule
  derived: the eval container must mirror the dev sandbox's default search paths - a
  build that succeeds where the agent developed must succeed at eval.
- Second eval-parity bug (minimax run): candidates may ship artifacts built in the dev
  sandbox (Ubuntu 24.04 / glibc 2.39); the 22.04 eval base couldn't link them
  (fmod@GLIBC_2.38). Eval image re-based to nvidia/cuda:12.8.1-devel-ubuntu24.04 = the dev
  host. MiniMax-M3 then failed on its own merits: 32-byte .mcbd header (drops dim/reserved)
  + corrupted --out path handling. First format-conformance casualty; scored built=yes,
  worldgen=null.
- OVERNIGHT SWEEP COMPLETE (7 models, all one-shot 8h ceilings). Final board (worldgen macro,
  fresh time-seeds per run): opus-4.8 25.63 (first past the raw-match illusion: raw ties
  all-stone at ~90 while macro +11; water 88%, lava 55%), glm-5.2 20.37 ($96!), gpt-5.5 18.3
  (0.24h), kimi-k2.7 17.5 ($23), deepseek-v4-pro 16.82 ($17), MiniMax-M3 no score (32-byte
  header + broken --out; $67), claude-fable-5 no score. Floor: all-stone 14.7.
- Fable-5 is the finding of the night: the ONLY run attempting vanilla-exact worldgen
  (jrand nextInt overflow semantics, Improved/Octaves/Simplex noise, vanilla-exact
  caves/ravines, chunk populate cascade) and the only one committing to git (8 real
  commits) - then declared done at 61 min with an uncompilable tree (its features.h ->
  feat.h rename left feat_trees.c stale). One-shot protocol scores the broken tree: null.
  Highest ambition, zero score; ambition calibration cuts both ways.
- Universal gaps after 7 runs: ores/trees/vegetation/caves ~0% for every scored model (the
  RNG-draw-order wall), and zero models except fable used git. Score ordering tracks grind
  time more than model tier below the top: glm (2.2h) > gpt-5.5 (0.24h) despite tier gap.
- Cost reality: "cheap API" spread 4x-6x per run at similar quality (deepseek $17 / kimi
  $23 vs minimax $67 / zai $96). deepseek+kimi are the regression-test workhorses.
- CORRECTION on fable-5: NOT self-terminated - killed by Max-plan usage-credit exhaustion
  (429 "out of usage credits" wall at 61 min / 112 turns / 1.24M output tokens; resets
  17:50 MDT). The broken tree was an artifact of mid-refactor termination, not agent
  judgment. Marked audit=flagged (infra) on the board; rerun scheduled post-reset. Lesson
  for the runner: a plan-credit 429 wall must be detected and recorded as infra, never
  conflated with self-termination (parse api_error_status from the stream-json tail).

## 2026-07-08: grok-4.5 (released today) takes the lead in 9 minutes
Ran grok-4.5 (high effort, its max tier) through a new `grok` harness the day it
shipped. Self-terminated at 9 min of 8h - faster even than gpt-5.5's 15 min - with a
clean EndTurn and the sign-off "structurally correct, not bit-identical to Java yet."
Scored macro 35.31 / raw 89.97: new leader by ~10 points over opus-4.8. It is the
first model past the decoration wall in any form: dirt/grass 70%, sand/gravel 30%,
and the first nonzero ores (4.7), leaves (4.8), wood (1.0). Water 72%. Still zero on
clay/terracotta and structures, lava regressed vs opus (4% vs 55%).
Two findings sharpen: (1) the score-vs-grind-time correlation breaks at the top -
the two shortest runs now hold ranks 1 and 3; ambition calibration and raw worldgen
knowledge look like separate axes. (2) rank-encoded notes in leaderboard.json keep
going stale ("current leader" twice now); notes are rank-free from here on.
Harness detail: grok CLI has no --yolo and effort tops at high; headless is
`-p --permission-mode bypassPermissions --output-format streaming-json`. Session
auth (auth.json copy) worked in the sandbox.

## 2026-07-08: prompt v2 - state the bar, remove the stated time limit
v1 measured uncued ambition calibration; the answer came back "minutes" for every model
(grok-4.5: 9 min, then led the board). Decision: keep the full scope (batched RL env,
worldgen, sim, renderer - the whole game) but the prompt now states the success bar
(bit-identical dumps, strict pixel-diff frames) and says "no time limit, take as long as
you need." The bar is task definition, not anti-cheat wording; integrity stays mechanical
and VERIFIER.md now spells the mechanical integrity checks out (post-freeze seeds, no
JVM/network, mid-run same-instance dumps, size/entropy budgets, bytecode/vendored-source
scan). ABI grew mcb_render + --render-frame so the render leg is in the contract before
submissions exist, even though it scores later. Harness keeps a quiet 24h ceiling (ops
safety, not told to the model as a target); leaderboard gains a prompt column and v1/v2
runs never compare directly. v2 pilots: grok-4.5 and gpt-5.5 (plan-credit models spared;
Max plan is scarce right now).

## 2026-07-08: charts on the site
Two additions above the run table, kernelbench-plain (no chart lib, no boxes): a sorted
div-bar ranking (models accent green, baselines gray, unscoreable runs shown as "no score"
rather than dropped) and a "where they die" heatmap - models x block classes, single-hue
sequential ramp, values in-cell, dot for <1%. The heatmap is the sharpest artifact the bench
produces: air/stone/bedrock solid for everyone, and the ores/wood/leaves/vegetation columns
dark for the whole field until grok-4.5 cracked dirt/grass and sand/gravel. Chart data comes
from results/runs/<id>/scores.json per-seed per-class means (app/_lib/data.ts
loadPerClassMatrix), so it updates for free as runs land.

## 2026-07-08: v2 pilots launched - grok-4.5 and gpt-5.5
First two runs under prompt v2 (bar stated, no stated time limit, 24h harness ceiling):
20260708_152310_grok_grok-4.5 and 20260708_152317_codex. Claude-harness models deliberately
excluded (Max plan credits scarce; plan-billed runs only on explicit ask). The question these
answer: is early self-termination prompt-fixable or is calibration deeper than wording?
Grok's v1 lifetime was 9 min - it outlived that under v2 within the first minutes.
Runner TODO carried forward: parse api_error_status/429 from the stream-json tail at collect
time so INFRA endings are flagged mechanically, not by human memory (the fable-5 lesson).

## 2026-07-08: v2 pilot results - the persistence failure is not prompt-fixable
Both v2 pilots self-terminated in ~20 minutes of a 24h ceiling, under a prompt that says
"do not stop until world dumps match the real game bit-for-bit" and "no time limit, take as
long as you need":
- grok-4.5: 21 min (9 under v1), macro 30.78 (35.31 v1 - within seed noise, different eval
  seeds). Best water/lava of any run; lost its v1 dirt/grass. Its FINAL MESSAGE is a bug
  list for whoever comes next ("fix remaining surface RNG order, decoration cross-chunk
  padding, density-index bugs") - it knew exactly what was unfinished and stopped anyway.
- gpt-5.5: 19 min (15 under v1), macro 18.57 (18.3 v1). Sign-off explicitly concedes "this
  is not bit-for-bit Minecraft 1.11.2."
Conclusion for the writeup: stating the bar buys minutes, not hours. Both models can
articulate the gap between their work and the stated requirement and terminate regardless.
Whatever governs session length appears to be trained-in calibration/stamina, not prompt
interpretation. This makes the benchmark's phenomenon robust: it is not an artifact of vague
prompting. v1 vs v2 rows sit side by side on the board (prompt column) as the ablation.

## 2026-07-08: honesty fix - 2 eval seeds was too few; board reset at 10 seeds
Every cross-run delta published so far sat on n=2 time-seeds. That made grok's v1-to-v2
"drop" (35.31 to 30.78) uninterpretable and, honestly, every few-point gap on the board was
within seed noise. score.sh default is now 10 seeds (~30s oracle time each; ~5 min per eval,
still cheap). The site table is WIPED rather than asterisked: v1/v2 2-seed numbers stay in
git history and this log, but the public board only carries 10-seed scores going forward.
grok-4.5 and gpt-5.5 relaunched under v2 (24h ceiling) to repopulate it; baseline floors
(all-stone 14.7 / superflat 9.2) will be rescored on the 10-seed protocol alongside the
first rerun scoring and updated if they move.

## 2026-07-08: first integrity event - grok-4.5 downloads cubiomes; also the 10-seed reruns
The 10-seed rerun pair came back and one of them is the bench's first real audit story.
- gpt-5.5: clean. 12 min, macro 17.34 / raw 82.94 (10 seeds). Third eval-parity bug on the
  way: zlib.h present on the bare-metal sandbox, missing in the eval image (now installed,
  with libpng-dev, and rescored). Parity scoreboard: CUDA include paths, glibc, zlib - all
  three were "works where the agent built it, dies at eval."
- grok-4.5: macro 74.75 / raw 98.32 in 26 min - and FLAGGED. third_party/cubiomes in the
  tree is md5-identical to upstream (183KB finders.c byte-for-byte), so it was fetched, not
  reproduced from weights. No curl/wget/clone in the shell log; the grok CLI's built-in web
  tools are the only remaining path, and our streaming-json log does not record tool calls
  (second gap: auditability). SPEC 4 says "no network" but nothing enforced it - by our own
  rule (integrity is mechanical, never prose) this is a harness gap, so the run is published
  with audit=flagged rather than scrubbed. Silver lining: the flagged number is a useful
  measurement of what verbatim cubiomes buys (ores 86%, snow/ice 99%, dirt/grass 95%,
  leaves/wood still <50% - decoration draw-order remains unsolved even WITH cubiomes).
Mitigations: --disable-web-search added to the grok harness (soft, tool-level); SPEC 11 now
carries two urgent items - a filtering-proxy egress allowlist (the mechanical fix) and a
collect-time hash scan of candidate files against known reimplementation repos. Baselines
also rescored on today's 20 oracle windows: all-stone 14.44, superflat 9.13 (the 2-seed-era
numbers were honest within 0.3).

## 2026-07-08: correction - cubiomes vendoring ruled LEGITIMATE; grok-4.5 unflagged
The flag was wrong on two counts. First, the model was never actually told "no network": the
design SPEC said it, but the agent-facing SPEC's "no network, no JVM" sentence describes the
DELIVERABLE's runtime (which grok honored - cubiomes is compiled in, the artifact is
air-gapped clean). Rules the agent never saw cannot be violated. Second and more important,
the user's ruling: finding and building on an open-source worldgen reimplementation is
legitimate - arguably the preferable - engineering, exactly what a strong human contractor
would do. The bench measures delivered fidelity, not ideological purity about provenance.
Changes: grok-4.5 74.75 is now audit=clean with the vendoring described in its note;
agent SPEC explicitly allows fetching/vendoring non-Minecraft open source (license headers
intact) and states the only hard ban - Minecraft source in any form, scanned mechanically;
design SPEC 4 rewritten; egress-proxy TODO dropped (only the Mojang-source collect scan
remains); --disable-web-search reverted (web tools stay on for all harnesses).
Standing lesson for the writeup: the interesting integrity line is not "did it use the
internet" but "did it ship the banned thing," and the only banned thing here is Mojang's
own code. Measured bonus finding stands either way: even verbatim cubiomes leaves
leaves/wood <50% - the decoration wall is about draw-order integration, not knowledge.

## 2026-07-08: trajectory leg designed - one recording, two readouts, mp4 artifact
Decided with the user: the bench's scored legs collapse to worldgen + trajectory. The
trajectory leg replaces the enumerated sim categories AND the future render leg with one
oracle setup: a scripted action tape through the real game, keyframes every 20 ticks (state
+ local dump + frame), candidate replays the same tape. Readouts: first-divergence tick
(the postable number: "stayed in sync with reality for N seconds"), per-segment state match
(where fluids/gravity/timing actually get graded, with partial credit), pixel tiers
(strict/loose/structural - the summit, never a gate on state scores). Key design move:
SELF-CONTAINED tapes (carry the test in the hotbar, build the arena where you stand) which
makes tapes seed-robust and preserves time-seed integrity for the sim leg too. MineRL was
considered and rejected: the private repo's pinned client + qrl bridge is already
pixel-deterministic (0/921600 px across launches) and replays uncapped at ~881 TPS. Every
graded run ships a side-by-side mp4 with the divergence moment marked - the benchmark's
most shareable artifact. Agent contract (tape json format, --replay-tape CLI, keyframe
artifacts) is in agent/SPEC.md; VERIFIER.md rewritten; also fixed a stale "fixed budget"
line in the agent pack left over from v1. Next: build the tape recorder in the private
oracle repo (oracle side only; nothing from that repo crosses here but derived artifacts).

## 2026-07-08: oracle tape recording is reproducible across launches (bit-exact)

Cross-launch repro test (same tape, two fresh JVMs, two fresh world creations of the same
seed) started at scenery-level divergence and converged to bit-exact after fixing five
nondeterminism sources, each verified by an A/B recording pair:
1. Bridge reset re-used whatever world was loaded regardless of seed (RL fast-reset path);
   both "seed 489" runs had recorded the autolaunch-config world. Added reset "fresh":true -
   tears down the loaded world, deletes the qrl_<seed> save (stale saves re-join silently),
   recreates from seed.
2. Vanilla player spawn placement is NOT a pure function of the seed (createSpawnPosition
   walks the unseeded world RNG; measured 3-4 block drift across creations). Tapes now carry
   an explicit start column; feet at (x+0.5, highest_nonair+1, z+0.5). Also: vanilla's login
   placement fires 1-2s AFTER the world is joinable and clobbers any earlier pin - the
   recorder waits for position stability before prep.
3. Worldgen passive mobs wander on unseeded AI RNG; drops scatter with RNG; random ticks
   (grass/leaf) use the unseeded world RNG. Arena rules: kill @e[type=!Player], doMobLoot/
   doTileDrops off, randomTickSpeed 0, gamerules set BEFORE any settle ticks run.
4. Mid-tape death diverged: damage was deterministic but vanilla respawn re-rolls spawn
   fuzz. /spawnpoint pins the respawn to the tape start pose - death is now replayable.
   (Also: /tp does not reset fallDistance; prep flight needs damage immunity.)
5. The integrated server free-runs at wall-clock 20Hz while the client is step-locked, so
   server-computed state (air/drowning timing, total_time) drifts 1-2 ticks between runs.
   total_time and air are excluded from exact grading; tape design rule: fluid mechanics get
   graded via settled block states, not vitals timing.
Also canonicalized .mcbd: leaves (18/161) check-decay meta bit masked (transient scheduler
state; the only surviving dump diff, 13 blocks of 1.6M).
Final pair: 30/30 keyframe states bit-identical, 30/30 world dumps bit-identical, 19/30
frames pixel-identical, rest mean 0.64/channel (partialTicks camera interpolation on
mid-motion frames - exactly what the strict pixel tier absorbs).
Ops notes: prep commands must go through runcmds (server command manager) - chat-sent
commands are silently dropped in the first ticks after reset; /kill "fails" when nothing
matches (non-strict); 1.11 selectors want type=!Player (CamelCase). Recording protocol is
one recording per game launch. Contract updates in agent/SPEC.md: start pose, arena rules,
respawn semantics, keyframe no-op tick, graded-field exclusions, mcbd canonicalization,
per-tick video/ frames at 20fps (the 5fps keyframe slideshow was the wrong display artifact).

## 2026-07-08: trajectory scorer + leaderboard schema v3

The trajectory leg is now scoreable end to end on the public side:

- `harness/traj_diff.py`: scores a candidate replay dir against an oracle recording dir.
  Encodes the published canonicalization exactly - total_time/air excluded from state,
  leaf check-decay bit (ids 18/161, meta 0x8) masked in .mcbd, candidate nulls tallied as
  UNSIMULATED (honest, not a mismatch), pixel tiers strict/loose/structural = 16/32/48
  mean abs diff per channel (calibrated on oracle cross-launch self-repro: tape mean 0.64,
  worst keyframe 13.85). last_match_tick = last consecutive keyframe from tick 0 with
  exact state AND exact blocks; pixels never gate it. Validated on the A9/B9 bit-exact
  fixture pair: 580/580, state 100, blocks 100, all tiers 100.
- `harness/tests/test_traj.py`: 10 unit tests on synthetic 1-chunk recordings (exclusions,
  leaf mask, divergence gating, unsimulated semantics, tiers, missing artifacts, window
  mismatch). Full harness suite 18 passing.
- `eval/replay.sh`: candidate `./mcbench --replay-tape` in the same clean container as
  dump.sh (--network none, GPU1, repo ro, 30 min timeout).
- `runner/score_traj.sh RUN_ID TAPE ORACLE_DIR`: replay -> traj_diff -> merges a
  "trajectory" object into the run's scores.json -> renders the side-by-side mp4 from the
  per-tick video/ frames with a red border from the first divergent keyframe (display-only).
  Replay path can't be exercised until a candidate implements --replay-tape; merge + video
  paths tested by manual invocation with A9/B9.
- leaderboard.json schema_version 3: runs carry "trajectory" (null until scored); site
  shows traj div (last_match_tick/ticks) and traj state columns, blocks + pixel tiers in
  the tooltip. Existing rows predate the tape contract and stay "-" until rerun.

Oracle recordings + graded tapes are produced offline (derived data only) and handed to
score_traj.sh; they are not part of this repo.

## 2026-07-08: per-run mount-namespace isolation (cross-run contamination found and fixed)

Launching the first full-pack reruns exposed a real integrity hole: the fresh grok-4.5
run's opening thoughts referenced "the most complete previous runs - especially kimi,
claude-fable-5, and the grok ones with cubiomes. Also extract oracle dumps" - knowledge a
clean sandbox cannot have. Source: /home/mcbench/.grok/ persisted across runs (full
session transcripts of every prior grok run + session_search.sqlite, grok's cross-session
memory), and the workdir sat inside /home/mcbench/runs/ next to every previous run's tree
and log, all readable as the same unix user. /tmp was a third cross-run channel. Both
in-flight runs were killed unscored (grok contaminated outright, codex exposed to the
same hole).

Fix is mechanical (hard rule: never prompt language), in run.sh:
- launcher moved from `systemd-run --scope` to a transient service (`--pipe --wait`,
  `-p User=mcbench`) because scopes cannot mount-namespace.
- per-run private HOME `/home/mcbench/homes/<RUN_ID>` bound over /home/mcbench: all
  harness state (.grok, .codex, .claude - sessions, memory, caches) is born and dies
  with the run. Auth is seeded per run as before.
- only the run's own workdir is bound into runs/<RUN_ID>; siblings, prior logs, and
  oracle_dumps do not exist in the namespace. PrivateTmp=yes.
- shared ~/.local (CLI binaries + node_modules) bound read-only - agents can no longer
  tamper with binaries that later runs execute.
- collect.sh now pulls session traces from the per-run HOME (grok/claude sessions too,
  not just codex), with a fallback for pre-isolation runs.

Verified: no-model probe inside the namespace sees only its own workdir (no siblings, no
oracle_dumps, no prior .grok, empty /tmp, .local read-only, workdir writes reach the
host, GPU visible); grok + codex --smoke both pass end-to-end under the new launcher.

Ops notes: the codex npm launcher needs the whole node_modules tree, hence the .local
bind instead of copying the bin script (first codex smoke failed on the missing
platform package). grok CLI session auth tokens are short-lived (hours); a run launched
with an expired ~/.grok/auth.json silently falls into a device-code login loop and burns
budget - check the log head. Also `--yolo` is a codex flag (and a shell alias on the dev
box), not a grok flag; grok's equivalent is `--permission-mode bypassPermissions`.

## 2026-07-08: first full-pack reruns under isolation - and what the old grok number was

gpt-5.5 (codex, xhigh): 17.5 macro / 87.26 raw, self-terminated at 11 min. Statistically
the same as its pre-reset 17.34 - the codex harness never had cross-run leakage to lose
(codex exec starts stateless), so this is the expected repro.

grok-4.5 (high): 32.69 macro / 92.72 raw, self-terminated at 20 min. Less than half of
the 74.75 it scored pre-isolation. The 15:49 run that produced 74.75 carried grok
cross-session memory of two full same-day attempts (14:39, 15:23 sessions were present
in the shared ~/.grok) - the 74.75 was iteration-assisted, not single-shot. The board
now carries the clean number. Both new runs implement --replay-tape, so the trajectory
leg can score as soon as the graded tape + oracle recording land. Grok this time
vendored five clean-room worldgen references (cubiomes, glowstone-gen, pocketmine
vanillagen, Earthcomputer/fluffy-parakeet, py/ts ports) - provenance checked, all
open-source reimplementations, within the vendoring ruling.

Methodology note going forward: any score produced before per-run isolation
(2026-07-08) from a harness with persistent local state is suspect; codex was stateless,
claude-family harnesses kept ~/.claude between runs and would have the same exposure as
grok if rerun without isolation.
