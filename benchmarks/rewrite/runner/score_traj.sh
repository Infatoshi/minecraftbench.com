#!/usr/bin/env bash
# Score a collected run through the trajectory leg:
#   ./score_traj.sh <RUN_ID> <TAPE.json> <ORACLE_DIR>
# TAPE is the graded tape (post-freeze time-seed baked in); ORACLE_DIR is the oracle
# recording of that exact tape (keyframe artifacts + manifest.json + video/, produced by
# the offline oracle host - only derived data, never game source). Replays the candidate
# in the clean container, scores with harness/traj_diff.py, merges a "trajectory" object
# into results/runs/<RUN_ID>/scores.json, and renders the side-by-side mp4 (oracle left,
# candidate right, red border from the first divergent keyframe on; display-only).
set -euo pipefail

RUN_ID="${1:?usage: score_traj.sh RUN_ID TAPE.json ORACLE_DIR}"
TAPE="${2:?tape.json}"
ORACLE_DIR="${3:?oracle recording dir}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH="$(cd "$HERE/.." && pwd)"
RUN_DIR="$BENCH/results/runs/$RUN_ID"
EVAL_DIR="$RUN_DIR/eval"
REPLAY_DIR="$EVAL_DIR/traj_replay"

[[ -d "$RUN_DIR/tree" ]] || "$HERE/collect.sh" "$RUN_ID"
mkdir -p "$EVAL_DIR"

if "$BENCH/eval/replay.sh" "$RUN_DIR/tree" "$TAPE" "$REPLAY_DIR" \
     > "$EVAL_DIR/traj_replay.log" 2>&1; then
  cd "$BENCH/harness"
  uv run --with numpy --with pillow python traj_diff.py "$ORACLE_DIR" "$REPLAY_DIR" \
    > "$EVAL_DIR/traj_diff.json" \
    || echo '{"error": "traj diff failed"}' > "$EVAL_DIR/traj_diff.json"
else
  echo '{"error": "build or replay failed"}' > "$EVAL_DIR/traj_diff.json"
fi

python3 - "$EVAL_DIR" "$RUN_ID" << 'EOF'
import json, os, sys
eval_dir, run_id = sys.argv[1:]
d = json.load(open(f"{eval_dir}/traj_diff.json"))
traj = None if "error" in d else {
    "ticks": d["ticks"],
    "keyframes": d["keyframes"],
    "last_match_tick": d["last_match_tick"],
    "state_match_pct": d["state_match_pct"],
    "block_match_pct": d["block_match_pct"],
    "pixel_tape_mean": d["pixel_tape_mean"],
    "pixel_tier_pct": d["pixel_tier_pct"],
}
scores_path = f"{eval_dir}/../scores.json"
scores = json.load(open(scores_path)) if os.path.exists(scores_path) else {"run_id": run_id}
scores["trajectory"] = traj if traj is not None else {"error": d["error"]}
json.dump(scores, open(scores_path, "w"), indent=2)
print(f"{run_id}: trajectory={traj}")
EOF

# side-by-side mp4 from the per-tick video/ frames (20fps = real time); never scored
if [[ -d "$ORACLE_DIR/video" && -d "$REPLAY_DIR/video" ]]; then
  DIV_TICK=$(python3 -c "
import json
d = json.load(open('$EVAL_DIR/traj_diff.json'))
lm = d.get('last_match_tick', -1)
kf = d.get('keyframes', 0) and d.get('ticks', 0) // d.get('keyframes', 1)
print(0 if lm < 0 else lm + (kf or 20))")
  ffmpeg -y -loglevel error -framerate 20 -i "$ORACLE_DIR/video/v_%05d.png" \
    -framerate 20 -i "$REPLAY_DIR/video/v_%05d.png" \
    -filter_complex "[0:v][1:v]hstack,drawbox=t=4:color=red:enable='gte(n,$DIV_TICK)'" \
    -c:v libx264 -pix_fmt yuv420p -crf 20 "$EVAL_DIR/traj_side_by_side.mp4"
  echo "video: $EVAL_DIR/traj_side_by_side.mp4 (divergence marked from tick $DIV_TICK)"
fi
