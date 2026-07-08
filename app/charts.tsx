"use client"

import { useState } from "react"

export type BarRow = {
  label: string
  value: number | null // null = no scoreable dump
  kind: "model" | "baseline"
  note: string
}

// Horizontal bars, sorted; models in the accent hue, baselines gray context.
export function MacroBars({ rows }: { rows: BarRow[] }) {
  const max = Math.max(...rows.map((r) => r.value ?? 0), 1)
  return (
    <div className="chart">
      <h2 className="chart-title">
        worldgen{" "}
        <span className="chart-subtitle">
          macro per-block-class accuracy vs the real game, mean over post-freeze
          time-seeds
        </span>
      </h2>
      <div className="chart-body">
        {rows.map((r) => (
          <div key={r.label} className="chart-row" title={r.note}>
            <div className="chart-row-label">{r.label}</div>
            <div className="chart-track">
              <div className="chart-bar-wrap">
                <div
                  className={
                    r.kind === "baseline" ? "chart-bar chart-bar-baseline" : "chart-bar"
                  }
                  style={{
                    width:
                      r.value == null
                        ? "0%"
                        : `${Math.max((r.value / max) * 100, 1.5)}%`,
                  }}
                />
              </div>
              <span className={r.value == null ? "chart-val chart-val-dnf" : "chart-val"}>
                {r.value == null ? "no score" : `${r.value.toFixed(1)}%`}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const RAMP = ["#232426", "#1d3512", "#2e5420", "#40752e", "#549740", "#6cc349", "#8fe363"]

function cellColor(v: number): string {
  if (v < 1) return RAMP[0] // empty slot: the model never places this class
  const i = 1 + Math.min(5, Math.floor((v / 100) * 6))
  return RAMP[i]
}

// Models x block classes. Sequential single-hue ramp; the near-empty columns ARE
// the story (the RNG-draw-order wall). Values in-cell for relief; table below.
export function ClassHeatmap({
  classes,
  rows,
}: {
  classes: string[]
  rows: { model: string; macro: number; perClass: Record<string, number> }[]
}) {
  const [hover, setHover] = useState<string | null>(null)
  return (
    <div className="chart">
      <h2 className="chart-title">
        where they die{" "}
        <span className="chart-subtitle">
          per-block-class accuracy %; dark column = nobody has cracked it
        </span>
      </h2>
      <div className="overflow-x-auto">
        <table className="heatmap">
          <thead>
            <tr>
              <th></th>
              {classes.map((c) => (
                <th key={c} className={hover === c ? "heatmap-col-active" : ""}>
                  <span className="heatmap-col-label">{c}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.model}>
                <td className="heatmap-model">{r.model}</td>
                {classes.map((c) => {
                  const v = r.perClass[c] ?? 0
                  return (
                    <td
                      key={c}
                      className="heatmap-cell"
                      onMouseEnter={() => setHover(c)}
                      onMouseLeave={() => setHover(null)}
                      title={`${r.model} - ${c}: ${v.toFixed(1)}%`}
                      style={{ background: cellColor(v) }}
                    >
                      <span className={v >= 50 ? "heatmap-val heatmap-val-dark" : "heatmap-val"}>
                        {v < 1 ? "·" : Math.round(v)}
                      </span>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
