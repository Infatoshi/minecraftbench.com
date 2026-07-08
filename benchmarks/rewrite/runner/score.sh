#!/usr/bin/env bash
# Score a collected run through the full worldgen leg:
#   ./score.sh <RUN_ID> [NSEEDS]
# Draws NSEEDS (default 10) fresh time-seeds (post-freeze by construction), generates the
# oracle world for each, dumps the candidate in the clean container, diffs, and writes
# results/runs/<RUN_ID>/scores.json. A candidate that fails to build/dump scores null.
set -euo pipefail

RUN_ID="${1:?usage: score.sh RUN_ID [NSEEDS]}"
NSEEDS="${2:-10}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH="$(cd "$HERE/.." && pwd)"
RUN_DIR="$BENCH/results/runs/$RUN_ID"
EVAL_DIR="$RUN_DIR/eval"

[[ -d "$RUN_DIR/tree" ]] || "$HERE/collect.sh" "$RUN_ID"
mkdir -p "$EVAL_DIR"

mapfile -t SEEDS < <(python3 -c "
import hashlib, time
t = time.time_ns()
for i in range($NSEEDS):
    print(int.from_bytes(hashlib.sha256(f'{t}:{i}'.encode()).digest()[:8], 'little') % (2**63))
")

cd "$BENCH/harness"
for seed in "${SEEDS[@]}"; do
  if [[ ! -f "$EVAL_DIR/oracle_$seed.mcbd" ]]; then
    uv run --with numpy --with nbt --with pyyaml python oracle_gen.py \
      --seed "$seed" --out "$EVAL_DIR/oracle_$seed.mcbd"
  fi
  read -r cx0 cz0 cx1 cz1 < <(uv run --with numpy python -c "
from mcbd import read_mcbd
d = read_mcbd('$EVAL_DIR/oracle_$seed.mcbd')
print(d.cx0, d.cz0, d.cx1, d.cz1)")
  if "$BENCH/eval/dump.sh" "$RUN_DIR/tree" "$seed" "$cx0" "$cz0" "$cx1" "$cz1" \
       "$EVAL_DIR/cand_$seed.mcbd" > "$EVAL_DIR/dump_$seed.log" 2>&1; then
    uv run --with numpy python diff.py "$EVAL_DIR/oracle_$seed.mcbd" "$EVAL_DIR/cand_$seed.mcbd" \
      > "$EVAL_DIR/diff_$seed.json" || echo '{"error": "diff failed"}' > "$EVAL_DIR/diff_$seed.json"
  else
    echo '{"error": "build or dump failed"}' > "$EVAL_DIR/diff_$seed.json"
  fi
done

python3 - "$EVAL_DIR" "$RUN_ID" "${SEEDS[@]}" << 'EOF'
import json, sys
eval_dir, run_id, *seeds = sys.argv[1:]
per_seed, macros, raws = {}, [], []
for s in seeds:
    m = json.load(open(f"{eval_dir}/diff_{s}.json"))
    per_seed[s] = m
    if "macro_accuracy_pct" in m:
        macros.append(m["macro_accuracy_pct"])
        raws.append(m["raw_match_pct"])
out = {
    "run_id": run_id,
    "seeds": seeds,
    "built": bool(macros),
    "worldgen_macro_pct": round(sum(macros) / len(macros), 2) if macros else None,
    "worldgen_raw_pct": round(sum(raws) / len(raws), 2) if raws else None,
    "per_seed": per_seed,
}
with open(f"{eval_dir}/../scores.json", "w") as f:
    json.dump(out, f, indent=2)
print(f"{run_id}: built={out['built']} macro={out['worldgen_macro_pct']} raw={out['worldgen_raw_pct']}")
EOF
