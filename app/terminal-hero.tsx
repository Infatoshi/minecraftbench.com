"use client"

import { useEffect, useState } from "react"

const PROMPT =
  'rewrite minecraft 1.11.2 from scratch in C/CUDA as a batched RL env. interface in INTERFACE.md, scoring in SCORING.md. go.'

const COMMANDS = [
  `claude -p "${PROMPT}" --model claude-fable-5`,
  `codex -p "${PROMPT}" --model gpt-5.5-codex`,
  `opencode -p "${PROMPT}" --model gemini-3.5-pro`,
  `claude -p "${PROMPT}" --model claude-opus-4-8`,
  `codex -p "${PROMPT}" --model grok-5-code`,
]

const TYPE_MS = 18
const DELETE_MS = 5
const HOLD_MS = 10000

export function TerminalHero() {
  const [text, setText] = useState("")
  const [cmdIdx, setCmdIdx] = useState(0)
  const [phase, setPhase] = useState<"typing" | "holding" | "deleting">(
    "typing",
  )

  useEffect(() => {
    const target = COMMANDS[cmdIdx]
    let t: ReturnType<typeof setTimeout>

    if (phase === "typing") {
      if (text.length < target.length) {
        t = setTimeout(() => setText(target.slice(0, text.length + 1)), TYPE_MS)
      } else {
        t = setTimeout(() => setPhase("deleting"), HOLD_MS)
      }
    } else if (phase === "deleting") {
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
        <span className="terminal-title">anvil: ~/minecraftbench</span>
      </div>
      <div className="terminal-body">
        <span className="terminal-ps1">$ </span>
        <span className="terminal-cmd">{text}</span>
        <span className="terminal-cursor" />
      </div>
    </div>
  )
}
