import fs from "node:fs"
import path from "node:path"

export type Task = {
  id: string
  title: string
  metric: string
}

export type ModelRow = {
  name: string
  score: number
  solved: number
  notes: string
}

export type Leaderboard = {
  schema_version: number
  bench: string
  date: string
  note: string
  tasks: Task[]
  models: ModelRow[]
}

export function loadSurvivalLeaderboard(): Leaderboard {
  const file = path.join(
    process.cwd(),
    "benchmarks",
    "survival",
    "results",
    "leaderboard.json",
  )
  return JSON.parse(fs.readFileSync(file, "utf8")) as Leaderboard
}
