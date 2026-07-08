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
BUDGET_HOURS=""
SMOKE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --harness) HARNESS="$2"; shift 2 ;;
    --budget-hours) BUDGET_HOURS="$2"; shift 2 ;;
    --smoke) SMOKE=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
[[ -n "$HARNESS" ]] || { echo "--harness required (codex)" >&2; exit 2; }
if [[ $SMOKE -eq 1 ]]; then
  BUDGET_S=300
else
  [[ -n "$BUDGET_HOURS" ]] || { echo "--budget-hours required (or --smoke)" >&2; exit 2; }
  BUDGET_S=$(( BUDGET_HOURS * 3600 ))
fi

SUFFIX=""
[[ $SMOKE -eq 1 ]] && SUFFIX="_smoke"
RUN_ID="$(date +%Y%m%d_%H%M%S)_${HARNESS}${SUFFIX}"
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
case "$HARNESS" in
  codex)
    sudo -u mcbench mkdir -p /home/mcbench/.codex
    sudo cp /home/infatoshi/.codex/auth.json /home/mcbench/.codex/auth.json
    sudo chown mcbench:mcbench /home/mcbench/.codex/auth.json
    sudo chmod 600 /home/mcbench/.codex/auth.json
    # shellcheck disable=SC2016  # $(cat prompt.txt) expands inside the sandbox shell, not here
    CMD='codex exec -m gpt-5.5 -c model_reasoning_effort=xhigh --dangerously-bypass-approvals-and-sandbox "$(cat prompt.txt)"'
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
  bash -c "cd '$WORKDIR' && timeout --signal=INT --kill-after=60 ${BUDGET_S} $CMD" \
  2>&1 | sudo -u mcbench tee "$LOG" || true

echo "--- run over; final repo state:"
sudo -u mcbench git -C "$WORKDIR" log --oneline | head -20
sudo -u mcbench git -C "$WORKDIR" status --short | head -20
echo "trace: $LOG"
echo "collect with: runner/collect.sh $RUN_ID"
