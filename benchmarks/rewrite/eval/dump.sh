#!/usr/bin/env bash
# Eval-time candidate dump in the clean container (VERIFIER.md step 2).
#   ./dump.sh <candidate_repo> <seed> <cx0> <cz0> <cx1> <cz1> <out.mcbd>
# Repo mounts read-only; build artifacts and the dump land in a scratch tmpfs / out dir.
# --network none: the candidate can never reach the oracle or anything else.
set -euo pipefail

REPO="${1:?candidate repo}"; SEED="${2:?seed}"
CX0="${3:?}"; CZ0="${4:?}"; CX1="${5:?}"; CZ1="${6:?}"
OUT="${7:?out.mcbd}"
OUTDIR="$(cd "$(dirname "$OUT")" && pwd)"
OUTNAME="$(basename "$OUT")"

docker run --rm --network none --gpus '"device=1"' \
  --cpus 24 --memory 64g --pids-limit 4096 \
  -v "$(cd "$REPO" && pwd):/repo:ro" \
  -v "$OUTDIR:/out" \
  mcbench-eval bash -c "
    set -e
    cp -r /repo /work/repo && cd /work/repo
    make -j
    timeout 600 ./mcbench --dump-world --seed $SEED \
      --cx0 $CX0 --cz0 $CZ0 --cx1 $CX1 --cz1 $CZ1 --out /out/$OUTNAME
  "
echo "dump: $OUT"
