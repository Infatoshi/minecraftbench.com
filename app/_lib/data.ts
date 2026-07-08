import fs from "node:fs"
import path from "node:path"

export type RunRow = {
  run_id: string
  model: string
  harness: string
  date: string
  built: boolean
  worldgen_macro_pct: number | null
  worldgen_raw_pct: number | null
  hours_used: number | null
  hours_granted: number | null
  cost_usd?: number | null
  prompt_version?: number
  audit: "clean" | "flagged" | "pending"
  note: string
  trace_url: string | null
}

export type BaselineRow = {
  name: string
  worldgen_macro_pct: number
  worldgen_raw_pct: number
  note: string
}

export type Leaderboard = {
  schema_version: number
  bench: string
  date: string
  note: string
  runs: RunRow[]
  baselines: BaselineRow[]
}

export function loadRewriteLeaderboard(): Leaderboard {
  const file = path.join(
    process.cwd(),
    "benchmarks",
    "rewrite",
    "results",
    "leaderboard.json",
  )
  return JSON.parse(fs.readFileSync(file, "utf8")) as Leaderboard
}

export type ClassRow = {
  model: string
  macro: number
  perClass: Record<string, number>
}

// Mean per-block-class accuracy across eval seeds, from each scored run's scores.json.
export function loadPerClassMatrix(board: Leaderboard): {
  classes: string[]
  rows: ClassRow[]
} {
  const rows: ClassRow[] = []
  const classSet = new Set<string>()
  for (const r of board.runs) {
    if (r.worldgen_macro_pct == null) continue
    const file = path.join(
      process.cwd(),
      "benchmarks",
      "rewrite",
      "results",
      "runs",
      r.run_id,
      "scores.json",
    )
    if (!fs.existsSync(file)) continue
    const s = JSON.parse(fs.readFileSync(file, "utf8")) as {
      seeds: string[]
      per_seed: Record<
        string,
        { per_class?: Record<string, { accuracy_pct: number }> }
      >
    }
    const acc: Record<string, number[]> = {}
    for (const seed of s.seeds) {
      const pc = s.per_seed[seed]?.per_class
      if (!pc) continue
      for (const [cls, v] of Object.entries(pc)) {
        ;(acc[cls] ??= []).push(v.accuracy_pct)
      }
    }
    const perClass: Record<string, number> = {}
    for (const [cls, vals] of Object.entries(acc)) {
      perClass[cls] = vals.reduce((a, b) => a + b, 0) / vals.length
      classSet.add(cls)
    }
    rows.push({ model: r.model, macro: r.worldgen_macro_pct, perClass })
  }
  rows.sort((a, b) => b.macro - a.macro)
  const ORDER = [
    "air",
    "stone-family",
    "bedrock",
    "dirt/grass",
    "sand/gravel",
    "water",
    "lava",
    "ores",
    "wood",
    "leaves",
    "vegetation",
    "snow/ice",
    "clay/terracotta",
    "structure-ish",
    "other",
  ]
  const classes = ORDER.filter((c) => classSet.has(c))
  return { classes, rows }
}
