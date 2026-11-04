#!/usr/bin/env bash
# make stop: the safety net. Stops a make start running in any terminal, or a background server. Safe to run twice.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
if alive "$RUN_DIR/start.pid" "start.sh"; then
  pid="$(cat "$RUN_DIR/start.pid")"
  kill -TERM "$pid" 2>/dev/null
  for _ in $(seq 1 60); do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
  echo "✔ Kanakku stopped"
  exit 0
fi
rm -f "$RUN_DIR/start.pid"
"$ROOT/scripts/down.sh"
remove_reverse
