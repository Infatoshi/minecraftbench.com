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
