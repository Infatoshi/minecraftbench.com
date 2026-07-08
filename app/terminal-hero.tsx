"use client"

import { useEffect, useState } from "react"

const GOAL =
  "rewrite minecraft 1.11.2 from scratch in C/CUDA as a batched RL env. interface in INTERFACE.md, scoring in SCORING.md. go."

// Real flags, verified against each CLI's current docs/help.
const COMMANDS = [
  'claude -p "$(cat GOAL.md)" --model claude-fable-5 --dangerously-skip-permissions',
  'codex exec -m gpt-5.5 --dangerously-bypass-approvals-and-sandbox "$(cat GOAL.md)"',
  'claude -p "$(cat GOAL.md)" --model claude-opus-4-8 --dangerously-skip-permissions',
  'grok -p --yolo "$(cat GOAL.md)"',
  'cursor agent --print --yolo --model composer-2 "$(cat GOAL.md)"',
]

const TYPE_MS = 18
const DELETE_MS = 5
const HOLD_MS = 10000

export function TerminalHero() {
  const [text, setText] = useState("")
  const [cmdIdx, setCmdIdx] = useState(0)
  const [phase, setPhase] = useState<"typing" | "deleting">("typing")

  useEffect(() => {
    const target = COMMANDS[cmdIdx]
    let t: ReturnType<typeof setTimeout>

    if (phase === "typing") {
      if (text.length < target.length) {
        t = setTimeout(() => setText(target.slice(0, text.length + 1)), TYPE_MS)
      } else {
        t = setTimeout(() => setPhase("deleting"), HOLD_MS)
      }
    } else {
      if (text.length > 0) {
        t = setTimeout(() => setText(text.slice(0, -1)), DELETE_MS)
      } else {
        setCmdIdx((cmdIdx + 1) % COMMANDS.length)
        setPhase("typing")
      }
    }

    return () => clearTimeout(t)
  }, [text, phase, cmdIdx])

  return (
    <div className="terminal">
      <div className="terminal-bar">
        <span className="terminal-dot" />
        <span className="terminal-dot" />
        <span className="terminal-dot" />
        <span className="terminal-title">3090: ~/minecraftbench</span>
      </div>
      <div className="terminal-body">
        <div className="terminal-static">
          <span className="terminal-ps1">$ </span>
          <span className="terminal-cmd">cat GOAL.md</span>
        </div>
        <div className="terminal-goal">{GOAL}</div>
        <div>
          <span className="terminal-ps1">$ </span>
          <span className="terminal-cmd">{text}</span>
          <span className="terminal-cursor" />
        </div>
      </div>
    </div>
  )
}
