import { loadRewriteLeaderboard } from "@/app/_lib/data"
import { TerminalHero } from "./terminal-hero"

export default function HomePage() {
  const board = loadRewriteLeaderboard()
  const topScore = Math.max(...board.models.map((m) => m.score))

  return (
    <div className="flex flex-col gap-12">
      <section className="flex flex-col gap-5">
        <h1 className="title-grass">minecraftbench.com</h1>
        <TerminalHero />
        <p className="text-[var(--color-fg-muted)] max-w-3xl leading-relaxed text-sm">
          One prompt, one budget, no Minecraft source, no network. Scored by
          dual execution against the real Java game on seeds drawn at eval
          time, and on fidelity-gated batched throughput. Methodology lives in{" "}
          <a href="https://github.com/Infatoshi/minecraftbench.com/blob/master/benchmarks/rewrite/SPEC.md">
            the repo
          </a>
          .
        </p>
        <div className="flex flex-wrap gap-3 text-xs">
          <span className="status-pill status-pill-warn">
            example data - first sweep coming soon
          </span>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-[var(--color-fg-bright)]">
          Rewrite <span className="text-[var(--color-fg-dim)]">·</span>{" "}
          <span className="text-sm font-normal text-[var(--color-fg-muted)]">
            {board.layers.length} scored layers, each strictly harder
          </span>
        </h2>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {board.layers.map((l) => (
            <div key={l.id} className="stat-box">
              <div className="text-sm text-[var(--color-fg-bright)] font-semibold">
                {l.title}
              </div>
              <div className="text-xs text-[var(--color-fg-muted)] mt-1">
                {l.metric}
              </div>
            </div>
          ))}
        </div>

        <div className="box overflow-x-auto p-0">
          <table className="term tabular">
            <thead>
              <tr>
                <th>#</th>
                <th>model</th>
                <th>composite</th>
                <th>layers cleared</th>
                <th className="w-1/3">relative</th>
              </tr>
            </thead>
            <tbody>
              {board.models.map((m, i) => (
                <tr key={m.name}>
                  <td className="text-[var(--color-fg-muted)]">{i + 1}</td>
                  <td className="font-mono text-[var(--color-fg-bright)]">
                    {m.name}
                  </td>
                  <td className={m.score === topScore ? "cell-winner" : "cell-score"}>
                    {m.score.toFixed(1)}
                  </td>
                  <td>
                    {m.solved}/{board.layers.length}
                  </td>
                  <td>
                    <div className="speed-bar">
                      <div
                        className={
                          m.score === topScore
                            ? "speed-fill speed-fill-winner"
                            : "speed-fill"
                        }
                        style={{ width: `${(m.score / topScore) * 100}%` }}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
