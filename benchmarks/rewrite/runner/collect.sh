#!/usr/bin/env bash
# Collect a finished run's artifacts out of the sandbox for eval + publishing.
#   ./collect.sh <RUN_ID> [dest]   (default dest: benchmarks/rewrite/results/runs/<RUN_ID>)
# Grabs: workdir (as a git bundle + a plain tree snapshot), stdout log, codex session jsonl.
set -euo pipefail

RUN_ID="${1:?usage: collect.sh RUN_ID [dest]}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${2:-$HERE/../results/runs/$RUN_ID}"
WORKDIR="/home/mcbench/runs/$RUN_ID"

mkdir -p "$DEST"
sudo -u mcbench git -C "$WORKDIR" bundle create "/tmp/mcbench_$RUN_ID.bundle" --all
sudo mv "/tmp/mcbench_$RUN_ID.bundle" "$DEST/repo.bundle"
sudo rsync -a --exclude .git "$WORKDIR/" "$DEST/tree/"
sudo cp "/home/mcbench/runs/$RUN_ID.log" "$DEST/stdout.log" 2>/dev/null || true
if sudo test -d /home/mcbench/.codex/sessions; then
  sudo rsync -a /home/mcbench/.codex/sessions/ "$DEST/sessions/"
fi
sudo chown -R "$(id -un):$(id -gn)" "$DEST"
echo "collected -> $DEST"
du -sh "$DEST"
