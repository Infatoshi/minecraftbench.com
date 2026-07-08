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
