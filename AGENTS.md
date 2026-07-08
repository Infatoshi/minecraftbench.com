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
  prompts; fix the harness instead (SPEC section 7).
- GPU work targets anvil GPU1 (RTX 3090, sm_86). Check `nvidia-smi` first - shared box.

## Site
- `bun install && bun run dev`. Build check: `bun run build`. Push to master = deploy.
- Leaderboard data: `benchmarks/rewrite/results/leaderboard.json` (schema-versioned). Placeholder
  until first sweep; keep the "example data" pill until real runs land.

## Style
No emojis, no em dashes. Minimal changes. UV only for Python. Tests/build must pass before done.
