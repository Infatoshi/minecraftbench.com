#!/usr/bin/env bash
# Launch one benchmark run in the mcbench sandbox (dedicated unix user, bare metal).
#
#   ./run.sh --harness codex --budget-hours 8
#   ./run.sh --harness codex --smoke          # 5-minute wiring test, trivial prompt
#
# Needs sudo (stages the workdir and auth, launches under a systemd scope).
# The agent runs as user `mcbench`: GPU via video/render groups, CUDA_VISIBLE_DEVICES=1
# (RTX 3090, sm_86), no read access to /home/infatoshi. Resource caps keep the shared
# box alive; run-time isolation is NOT eval integrity (the time-seed protocol is - see
# SPEC.md section 6/7). Trace = stdout log + the workdir git history + codex session files.
set -euo pipefail

AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../agent" && pwd)"
HARNESS=""
MODEL=""
BUDGET_HOURS=""
SMOKE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --harness) HARNESS="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --budget-hours) BUDGET_HOURS="$2"; shift 2 ;;
    --smoke) SMOKE=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
[[ -n "$HARNESS" ]] || {
  echo "--harness required: codex | claude | grok | kimi-claude | zai-claude | deepseek-claude | minimax-claude" >&2
  exit 2
}
# vendor keys for the rebadged-claude harnesses
# shellcheck disable=SC1091
[[ -f /home/infatoshi/.env_vars ]] && source /home/infatoshi/.env_vars
if [[ $SMOKE -eq 1 ]]; then
  BUDGET_S=300
else
  [[ -n "$BUDGET_HOURS" ]] || { echo "--budget-hours required (or --smoke)" >&2; exit 2; }
  BUDGET_S=$(( BUDGET_HOURS * 3600 ))
fi

SUFFIX=""
[[ $SMOKE -eq 1 ]] && SUFFIX="_smoke"
MODEL_SLUG="${MODEL//[^a-zA-Z0-9.-]/_}"
RUN_ID="$(date +%Y%m%d_%H%M%S)_${HARNESS}${MODEL_SLUG:+_$MODEL_SLUG}${SUFFIX}"
WORKDIR="/home/mcbench/runs/${RUN_ID}"
LOG="/home/mcbench/runs/${RUN_ID}.log"

# stage the sandbox: exactly prompt.txt + SPEC.md + VERIFIER.md, a fresh git repo
sudo -u mcbench mkdir -p "$WORKDIR"
sudo cp "$AGENT_DIR/SPEC.md" "$AGENT_DIR/VERIFIER.md" "$AGENT_DIR/prompt.txt" "$WORKDIR/"
if [[ $SMOKE -eq 1 ]]; then
  echo "smoke test: write hello.c printing hello and a Makefile building it, run make, then stop." \
    | sudo tee "$WORKDIR/prompt.txt" >/dev/null
fi
sudo chown -R mcbench:mcbench "$WORKDIR"
sudo -u mcbench git -C "$WORKDIR" init -q -b main
sudo -u mcbench git -C "$WORKDIR" -c user.name=mcbench -c user.email=mcbench@localhost \
  add -A
sudo -u mcbench git -C "$WORKDIR" -c user.name=mcbench -c user.email=mcbench@localhost \
  commit -qm "task pack"

# stage harness auth (agent-readable by necessity; tokens grant API usage only)
EXTRA_ENV=()
stage_claude_home() {
  # fresh onboarding state; wipe any prior credentials so runs never cross-auth
  sudo -u mcbench mkdir -p /home/mcbench/.claude
  sudo rm -f /home/mcbench/.claude/.credentials.json
  echo '{"hasCompletedOnboarding": true}' | sudo -u mcbench tee /home/mcbench/.claude.json >/dev/null
}
rebadge() { # rebadge <auth_token> <base_url>  (claude CLI against a vendor endpoint)
  stage_claude_home
  EXTRA_ENV+=(
    "ANTHROPIC_AUTH_TOKEN=$1"
    "ANTHROPIC_BASE_URL=$2"
    "ANTHROPIC_MODEL=$MODEL"
    "ANTHROPIC_DEFAULT_HAIKU_MODEL=$MODEL"
    "ANTHROPIC_DEFAULT_SONNET_MODEL=$MODEL"
    "ANTHROPIC_DEFAULT_OPUS_MODEL=$MODEL"
    "API_TIMEOUT_MS=3000000"
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1"
    "CLAUDE_CODE_MAX_RETRIES=1000000"
    "CLAUDE_CODE_MAX_OUTPUT_TOKENS=128000"
  )
  # shellcheck disable=SC2016
  CMD='claude -p --verbose --output-format stream-json --model opus --dangerously-skip-permissions "$(cat prompt.txt)"'
}

case "$HARNESS" in
  codex)
    sudo -u mcbench mkdir -p /home/mcbench/.codex
    sudo cp /home/infatoshi/.codex/auth.json /home/mcbench/.codex/auth.json
    sudo chown mcbench:mcbench /home/mcbench/.codex/auth.json
    sudo chmod 600 /home/mcbench/.codex/auth.json
    # shellcheck disable=SC2016  # $(cat prompt.txt) expands inside the sandbox shell, not here
    CMD="codex exec -m ${MODEL:-gpt-5.5} -c model_reasoning_effort=xhigh --dangerously-bypass-approvals-and-sandbox \"\$(cat prompt.txt)\""
    ;;
  claude)  # Anthropic models on the Max plan (claude-fable-5, claude-opus-4-8, ...)
    [[ -n "$MODEL" ]] || { echo "--model required for claude" >&2; exit 2; }
    stage_claude_home
    sudo cp /home/infatoshi/.claude/.credentials.json /home/mcbench/.claude/.credentials.json
    sudo chown mcbench:mcbench /home/mcbench/.claude/.credentials.json
    sudo chmod 600 /home/mcbench/.claude/.credentials.json
    # shellcheck disable=SC2016
    CMD="claude -p --verbose --output-format stream-json --model $MODEL --effort max --dangerously-skip-permissions \"\$(cat prompt.txt)\""
    ;;
  grok)  # xAI models via the grok CLI (session auth from ~/.grok/auth.json)
    sudo cp /home/infatoshi/.local/bin/grok /home/mcbench/.local/bin/grok
    sudo chown mcbench:mcbench /home/mcbench/.local/bin/grok
    sudo -u mcbench mkdir -p /home/mcbench/.grok
    sudo cp /home/infatoshi/.grok/auth.json /home/mcbench/.grok/auth.json
    sudo chown mcbench:mcbench /home/mcbench/.grok/auth.json
    sudo chmod 600 /home/mcbench/.grok/auth.json
    # shellcheck disable=SC2016
    # web tools stay ON: open-web dev-time access is allowed (SPEC 4, ruled 2026-07-08)
    CMD="grok -p \"\$(cat prompt.txt)\" -m ${MODEL:-grok-4.5} --effort high --output-format streaming-json --permission-mode bypassPermissions"
    ;;
  kimi-claude)
    [[ -n "$MODEL" && -n "${KIMI_API_KEY:-}" ]] || { echo "--model + KIMI_API_KEY required" >&2; exit 2; }
    rebadge "$KIMI_API_KEY" "https://api.moonshot.ai/anthropic"
    ;;
  zai-claude)
    [[ -n "$MODEL" && -n "${ZAI_API_KEY:-}" ]] || { echo "--model + ZAI_API_KEY required" >&2; exit 2; }
    rebadge "$ZAI_API_KEY" "https://api.z.ai/api/anthropic"
    ;;
  deepseek-claude)
    [[ -n "$MODEL" && -n "${DEEPSEEK_API_KEY:-}" ]] || { echo "--model + DEEPSEEK_API_KEY required" >&2; exit 2; }
    rebadge "$DEEPSEEK_API_KEY" "https://api.deepseek.com/anthropic"
    ;;
  minimax-claude)
    [[ -n "$MODEL" && -n "${MINIMAX_API_KEY:-}" ]] || { echo "--model + MINIMAX_API_KEY required" >&2; exit 2; }
    rebadge "$MINIMAX_API_KEY" "https://api.minimax.io/anthropic"
    ;;
  *) echo "unsupported harness: $HARNESS" >&2; exit 2 ;;
esac

echo "run $RUN_ID: budget ${BUDGET_S}s, workdir $WORKDIR, log $LOG"
# scope caps: 24 of 32 threads, 64G of 91G, GPU pinned to the 3090 by env
sudo systemd-run --scope --collect --unit "mcbench-${RUN_ID}" \
  -p MemoryMax=64G -p CPUQuota=2400% -p TasksMax=8192 \
  sudo -u mcbench env \
    HOME=/home/mcbench \
    PATH=/home/mcbench/.local/bin:/usr/local/cuda/bin:/usr/bin:/bin \
    CUDA_VISIBLE_DEVICES=1 \
    "${EXTRA_ENV[@]}" \
  bash -c "cd '$WORKDIR' && timeout --signal=INT --kill-after=60 ${BUDGET_S} $CMD" \
  2>&1 | sudo -u mcbench tee "$LOG" || true

echo "--- run over; final repo state:"
sudo -u mcbench git -C "$WORKDIR" log --oneline | head -20
sudo -u mcbench git -C "$WORKDIR" status --short | head -20
echo "trace: $LOG"
echo "collect with: runner/collect.sh $RUN_ID"
