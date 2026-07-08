import { loadSurvivalLeaderboard } from "@/app/_lib/data"

export default function HomePage() {
  const board = loadSurvivalLeaderboard()
  const topScore = Math.max(...board.models.map((m) => m.score))

  return (
    <div className="flex flex-col gap-12">
      <section className="flex flex-col gap-4">
        <h1 className="text-3xl sm:text-4xl font-bold text-[var(--color-fg-bright)]">
          minecraftbench.com
        </h1>
        <p className="text-[var(--color-fg-muted)] max-w-3xl leading-relaxed">
          Open agentic Minecraft benchmark results. Frontier LLM agents are
          dropped into vanilla survival Minecraft and graded on what they can
          actually do: gather, craft, build, survive. Every run ships with full
          agent transcripts, the harness source, and machine-readable results.
        </p>
        <div className="flex flex-wrap gap-3 text-xs">
          <span className="status-pill status-pill-warn">
            example data — first real sweep coming soon
          </span>
        </div>
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-xl font-bold text-[var(--color-fg-bright)]">
          Survival <span className="text-[var(--color-fg-dim)]">·</span>{" "}
          <span className="text-sm font-normal text-[var(--color-fg-muted)]">
            {board.tasks.length} tasks, vanilla survival, hard difficulty
          </span>
        </h2>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {board.tasks.map((t) => (
            <div key={t.id} className="stat-box">
              <div className="text-sm text-[var(--color-fg-bright)] font-semibold">
                {t.title}
              </div>
              <div className="text-xs text-[var(--color-fg-muted)] mt-1">
                metric: {t.metric}
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
                <th>score</th>
                <th>tasks solved</th>
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
                    {m.solved}/{board.tasks.length}
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
        <p className="text-xs text-[var(--color-fg-dim)]">
          Placeholder leaderboard rendered from{" "}
          <code>benchmarks/survival/results/leaderboard.json</code> at build
          time — swap in real run data and push to update the site.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-xl font-bold text-[var(--color-fg-bright)]">
          How it works
        </h2>
        <div className="grid sm:grid-cols-3 gap-3">
          <div className="box">
            <div className="text-[var(--color-accent)] font-semibold text-sm mb-1">
              1. Harness
            </div>
            <p className="text-xs text-[var(--color-fg-muted)] leading-relaxed">
              Each agent controls a Minecraft player through a scripted
              interface (e.g. Mineflayer bot) inside a sandboxed vanilla
              server. Same seed, same spawn, same tool budget for every model.
            </p>
          </div>
          <div className="box">
            <div className="text-[var(--color-accent)] font-semibold text-sm mb-1">
              2. Tasks
            </div>
            <p className="text-xs text-[var(--color-fg-muted)] leading-relaxed">
              Objective tasks are checked programmatically (inventory, world
              state); build-quality tasks are rubric-graded with published
              rubrics and screenshots.
            </p>
          </div>
          <div className="box">
            <div className="text-[var(--color-accent)] font-semibold text-sm mb-1">
              3. Artifacts
            </div>
            <p className="text-xs text-[var(--color-fg-muted)] leading-relaxed">
              Every run publishes its full agent transcript, world snapshots,
              and machine-readable scores. What is on disk in the repo is what
              is on this site.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}
