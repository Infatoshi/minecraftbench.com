#!/usr/bin/env bash
# Eval-time candidate tape replay in the clean container (VERIFIER.md: trajectory metric).
#   ./replay.sh <candidate_repo> <tape.json> <outdir>
# Same isolation as dump.sh: repo read-only, --network none, no JVM, GPU1. The candidate's
# ./mcbench --replay-tape writes keyframe artifacts + per-tick video/ frames into <outdir>.
set -euo pipefail

REPO="${1:?candidate repo}"
TAPE="${2:?tape.json}"
OUTDIR="${3:?outdir}"
mkdir -p "$OUTDIR"
OUTDIR="$(cd "$OUTDIR" && pwd)"
TAPE="$(cd "$(dirname "$TAPE")" && pwd)/$(basename "$TAPE")"

docker run --rm --network none --gpus '"device=1"' \
  --cpus 24 --memory 64g --pids-limit 4096 \
  -v "$(cd "$REPO" && pwd):/repo:ro" \
  -v "$TAPE:/tape.json:ro" \
  -v "$OUTDIR:/out" \
  mcbench-eval bash -c "
    set -e
    cp -r /repo /work/repo && cd /work/repo
    make -j
    timeout 1800 ./mcbench --replay-tape /tape.json --outdir /out
  "
echo "replay: $OUTDIR"
