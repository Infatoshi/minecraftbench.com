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
