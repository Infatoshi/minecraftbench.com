import fs from "node:fs"
import path from "node:path"

export type Layer = {
  id: string
  title: string
  metric: string
}

export type ModelRow = {
  name: string
  score: number
  solved: number
  notes: string
  hours_used?: number
  hours_granted?: number
}

export type Leaderboard = {
  schema_version: number
  bench: string
  date: string
  note: string
  layers: Layer[]
  baselines: {
    name: string
    note: string
    raw_match_pct?: number
    macro_acc_pct?: number
  }[]
  models: ModelRow[]
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
