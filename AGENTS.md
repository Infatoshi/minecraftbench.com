# minecraftbench.com (AGENTS.md)

<!-- machine: anvil, path: ~/minecraftbench.com -->

Home: anvil-primary, canonical at `anvil:~/minecraftbench.com`; public remote
`github.com/Infatoshi/minecraftbench.com` (Vercel auto-deploys master). CLAUDE.md symlinks here.

Monorepo, kernelbench.com shape: `app/` = Next.js site (reads `benchmarks/*/results/` at build
time), `benchmarks/rewrite/` = the benchmark. Read `benchmarks/rewrite/SPEC.md` FIRST for any
bench work - it is the design of record (task, ABI, scoring, threat model). Log decisions in
`benchmarks/rewrite/DEVLOG.md`.

## Hard rules
- NEVER vendor, quote, or copy anything from `~/dev/minecraft/mc-1.11.2-env` into this repo or
  into agent-visible context: it bundles decompiled Mojang source (illegal to redistribute) and
  this repo + its traces are PUBLIC. Only derived data crosses over (block grids, state CSVs,
  frames, scores).
- Eval integrity is mechanical, never prompt language. Do not add anti-cheat wording to task
  prompts; fix the harness instead (SPEC section 7). Stating the success BAR is task
  definition and allowed (prompt v2); anti-cheat threats/warnings are not.
- GPU work targets anvil GPU1 (RTX 3090, sm_86). Check `nvidia-smi` first - shared box.
- NO claude-fable-5 runs on this benchmark (user directive 2026-07-08). Plan-billed claude
  harness runs (opus etc.) only when the user explicitly asks - Max credits are scarce.
- The prompt is versioned (SPEC section 3). v1/v2 scores never compare. `agent/prompt.txt` is
  the single prompt file; `app/terminal-hero.tsx` PROMPT must match it verbatim - change both
  or neither.

## Runs (benchmarks/rewrite/runner/)
- `run.sh --harness codex|claude|grok|kimi-claude|zai-claude|deepseek-claude|minimax-claude
  [--model M] --budget-hours N` (24h ceiling under v2). ALWAYS `--smoke` a new harness first.
  Then `collect.sh <run_id>` and `score.sh <run_id>`; runs live in /home/mcbench/runs/ (sudo).
- Before recording a run as self-terminated, check the stream-json log tail for
  api_error_status/429: credit-wall endings are INFRA + flagged, never a score (fable-5
  lesson). Eval-container parity rule: a build that succeeds where the agent developed must
  succeed at eval (CPATH/LIBRARY_PATH for CUDA headers, ubuntu24.04 glibc - both bitten once).
- leaderboard.json run notes are rank-free (no "leader"/"current best" - they rot; rank lives
  in the sorted table). `results/runs/` is gitignored EXCEPT `*/scores.json` (the charts need
  it in the repo - Vercel builds from git, not this disk); full traces are not yet published.
- pkill on this box: bracket-escape the pattern (`pkill -f "[n]ext-server"`) or the command
  matches its own shell and kills it (exit 144).

## Site
- `bun install && bun run dev`. Build check: `bun run build`. Push to master = deploy.
- Leaderboard data: `benchmarks/rewrite/results/leaderboard.json` (schema-versioned). Charts
  read `results/runs/<id>/scores.json` (per-class means) via app/_lib/data.ts - keep scored
  runs' scores.json in the repo or the heatmap row vanishes.
- Adding a leaderboard column: the baseline rows in app/page.tsx need a matching `<td>-</td>`
  (misaligned twice already).

## Style
No emojis, no em dashes. Minimal changes. UV only for Python. Tests/build must pass before done.
