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
