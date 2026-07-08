import { loadPerClassMatrix, loadRewriteLeaderboard } from "@/app/_lib/data"
import { ClassHeatmap, MacroBars, type BarRow } from "./charts"
import { TerminalHero } from "./terminal-hero"

export default function HomePage() {
  const board = loadRewriteLeaderboard()
  const best = Math.max(
    ...board.runs
      .filter((r) => r.worldgen_macro_pct != null)
      .map((r) => r.worldgen_macro_pct as number),
  )
  const matrix = loadPerClassMatrix(board)
  const barRows: BarRow[] = [
    ...board.runs.map(
      (r): BarRow => ({
        label: r.model,
        value: r.worldgen_macro_pct,
        kind: "model",
        note: r.note,
      }),
    ),
    ...board.baselines.map(
      (b): BarRow => ({
        label: `baseline: ${b.name}`,
        value: b.worldgen_macro_pct,
        kind: "baseline",
        note: b.note,
      }),
    ),
  ].sort((a, b) => (b.value ?? -1) - (a.value ?? -1))

  return (
    <div className="flex flex-col gap-10">
      <section className="flex flex-col gap-5">
        <h1 className="title-grass">minecraftbench.com</h1>
        <TerminalHero />
      </section>

      <section>
        <MacroBars rows={barRows} />
      </section>

      {matrix.rows.length > 0 && (
        <section>
          <ClassHeatmap classes={matrix.classes} rows={matrix.rows} />
        </section>
      )}

      <section className="overflow-x-auto">
        <table className="term tabular text-xs">
          <thead>
            <tr>
              <th>model</th>
              <th>harness</th>
              <th>date</th>
              <th>built</th>
              <th>worldgen</th>
              <th>budget</th>
              <th>cost</th>
              <th>audit</th>
              <th>note</th>
              <th>trace</th>
            </tr>
          </thead>
          <tbody>
            {board.runs.map((r) => (
              <tr key={r.run_id}>
                <td className="font-mono text-[var(--color-fg-bright)]">
                  {r.model}
                </td>
                <td>{r.harness}</td>
                <td className="text-[var(--color-fg-muted)]">{r.date}</td>
                <td className={r.built ? "cell-score" : "cell-fail"}>
                  {r.built ? "yes" : "no"}
                </td>
                <td
                  className={
                    r.worldgen_macro_pct === best ? "cell-winner" : "cell-score"
                  }
                  title={
                    r.worldgen_raw_pct != null
                      ? `raw block match ${r.worldgen_raw_pct.toFixed(1)}%`
                      : undefined
                  }
                >
                  {r.worldgen_macro_pct != null
                    ? `${r.worldgen_macro_pct.toFixed(1)}%`
                    : "-"}
                </td>
                <td className="text-[var(--color-fg-muted)]">
                  {r.hours_used != null && r.hours_granted != null
                    ? `${r.hours_used}h / ${r.hours_granted}h`
                    : "-"}
                </td>
                <td className="text-[var(--color-fg-muted)]">
                  {r.cost_usd != null ? `$${r.cost_usd.toFixed(0)}` : "-"}
                </td>
                <td
                  className={
                    r.audit === "flagged"
                      ? "cell-fail"
                      : "text-[var(--color-fg-muted)]"
                  }
                >
                  {r.audit}
                </td>
                <td
                  className="text-[var(--color-fg-muted)] max-w-md"
                  title={r.note}
                >
                  {r.note}
                </td>
                <td>
                  {r.trace_url ? (
                    <a href={r.trace_url} target="_blank" rel="noopener">
                      trace
                    </a>
                  ) : (
                    <span className="text-[var(--color-fg-dim)]">-</span>
                  )}
                </td>
              </tr>
            ))}
            {board.baselines.map((b) => (
              <tr key={b.name} className="opacity-60">
                <td className="font-mono">baseline: {b.name}</td>
                <td>-</td>
                <td>-</td>
                <td>-</td>
                <td title={`raw block match ${b.worldgen_raw_pct.toFixed(1)}%`}>
                  {b.worldgen_macro_pct.toFixed(1)}%
                </td>
                <td>-</td>
                <td>-</td>
                <td>-</td>
                <td className="text-[var(--color-fg-muted)] max-w-md" title={b.note}>
                  {b.note}
                </td>
                <td>-</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}
