# minecraftbench.com

<!-- machine: anvil, path: ~/minecraftbench.com -->

Agentic Minecraft-rewrite benchmark for autonomous LLM coding agents. Same monorepo shape as
[kernelbench.com](https://kernelbench.com): the Next.js site reads benchmark results straight
from `benchmarks/*/results/` at build time; push to master and Vercel rebuilds.

The bench: one prompt - rewrite Minecraft 1.11.2 from scratch in C/CUDA as a PufferLib-style
batched RL environment for a pinned RTX 3090 (sm_86). Judged by time-seed dual execution against
the real Java game (block/state diffs) and fidelity-gated batched throughput. Design of record:
`benchmarks/rewrite/SPEC.md`. Currently planning phase; the leaderboard is placeholder data.

## Layout

```
.
├── app/                    Next.js website (app/_lib/data.ts reads benchmark data at build time)
├── public/                 Website static assets
└── benchmarks/
    └── rewrite/
        ├── SPEC.md         Design of record: task, interface ABI, scoring, threat model.
        ├── DEVLOG.md       Decisions, dead ends, lessons.
        ├── results/
        │   ├── leaderboard.json    Schema-versioned, machine-readable (drives the site).
        │   └── annotations/        Per-run YAML audit commentary (clean / leak / hack).
        ├── harness/        Eval orchestration (time-seed draw, dual execution, diffing). TBD.
        ├── baselines/      Trivial reference candidates (all-stone, superflat, biomes-only). TBD.
        └── tapes/          Action-tape corpus for sim fidelity. TBD.
```

The oracle (the real Java 1.11.2 game + qrl bridge + world diff tooling) lives in a PRIVATE repo
(`Infatoshi/mc-1.11.2-env`) because it bundles decompiled Mojang source. This repo only ever
contains derived data: block grids, state traces, scores, transcripts.

## Running the website locally

```bash
bun install
bun run dev
```

## Deploying

Vercel native GitHub integration; every push to `master` auto-deploys. Domain at Porkbun,
nameservers pointed at Vercel (`ns1/ns2.vercel-dns.com`).
