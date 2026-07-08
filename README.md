# minecraftbench.com

<!-- machine: anvil, path: /home/infatoshi/minecraftbench.com -->

Agentic Minecraft benchmarks for autonomous LLM agents. Same shape as
[kernelbench.com](https://kernelbench.com): a Next.js site that reads
benchmark results straight from `benchmarks/*/results/` at build time.

Currently ships an EXAMPLE placeholder leaderboard — replace
`benchmarks/survival/results/leaderboard.json` with real run data and push;
Vercel rebuilds.

## Layout

```
.
├── app/                    Next.js website (app/_lib/data.ts reads benchmark data at build time)
└── benchmarks/
    └── survival/
        └── results/
            └── leaderboard.json    Schema-versioned, machine-readable (drives the site)
```

## Running locally

```bash
bun install
bun run dev
```

## Deploying

Vercel native GitHub integration; every push to `master` auto-deploys.
Domain registered at Porkbun with nameservers pointed at Vercel
(`ns1.vercel-dns.com` / `ns2.vercel-dns.com`).
