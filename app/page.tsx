import { loadRewriteLeaderboard } from "@/app/_lib/data"

export default function HomePage() {
  const board = loadRewriteLeaderboard()
  const topScore = Math.max(...board.models.map((m) => m.score))

  return (
    <div className="flex flex-col gap-12">
      <section className="flex flex-col gap-4">
        <h1 className="title-grass">minecraftbench.com</h1>
        <p className="text-[var(--color-fg-muted)] max-w-3xl leading-relaxed">
          One prompt: rewrite Minecraft 1.11.2 from scratch in C/CUDA as a
          batched, PufferLib-style RL environment for a pinned RTX 3090. An
          autonomous LLM coding agent gets a toolchain, a black-box oracle CLI,
          and a budget - no Minecraft source, no network. It is judged by dual
          execution against the real Java game on seeds derived from the clock
          at eval time, and on fidelity-gated batched throughput. We bet
          frontier models cannot do this end to end. This bench measures how
          far they get.
        </p>
        <div className="flex flex-wrap gap-3 text-xs">
          <span className="status-pill status-pill-warn">
            example data - first sweep (gpt-5.5) coming soon
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
        <p className="text-xs text-[var(--color-fg-dim)]">
          Placeholder leaderboard rendered from{" "}
          <code>benchmarks/rewrite/results/leaderboard.json</code> at build
          time. Scores are macro-averaged per-block-class accuracy above
          published trivial baselines (all-stone, superflat, biomes-only) -
          never raw block match.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-[var(--color-fg-bright)]">
          Why it cannot be reward-hacked
        </h2>
        <div className="grid sm:grid-cols-3 gap-3">
          <div className="box">
            <div className="text-[var(--color-accent)] font-semibold text-sm mb-1">
              Time-seed dual execution
            </div>
            <p className="text-xs text-[var(--color-fg-muted)] leading-relaxed">
              Eval seeds are hashed from the wallclock after the submission is
              frozen. The candidate dumps its world first, in a clean container
              with no JVM and no network; the real Java game generates truth
              afterwards. No golden exists before eval starts, so there is
              nothing to memorize or embed.
            </p>
          </div>
          <div className="box">
            <div className="text-[var(--color-accent)] font-semibold text-sm mb-1">
              Same-instance throughput gating
            </div>
            <p className="text-xs text-[var(--color-fg-muted)] leading-relaxed">
              Mid-throughput-run, random envs from the running batch are frozen
              and dumped through the same ABI producing the SPS number, then
              diffed against the oracle. A fast-fake step path or stub sim
              fails the very run it is trying to score.
            </p>
          </div>
          <div className="box">
            <div className="text-[var(--color-accent)] font-semibold text-sm mb-1">
              Baseline-corrected metrics
            </div>
            <p className="text-xs text-[var(--color-fg-muted)] leading-relaxed">
              Raw block match is base-rate gameable (all-stone scores ~85%).
              Scores are macro-averaged per block class, reported per layer,
              and shown as skill above published trivial baselines.
            </p>
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-[var(--color-fg-bright)]">
          Artifacts
        </h2>
        <p className="text-sm text-[var(--color-fg-muted)] max-w-3xl leading-relaxed">
          Every run will publish its full agent transcript, the submission
          source, machine-readable per-layer scores, and audit annotations
          (clean / leak / hack). The oracle is the real Java game running
          privately; only derived data (block grids, state traces) is
          published - no Minecraft source ever enters the agent context or the
          traces.
        </p>
      </section>
    </div>
  )
}
