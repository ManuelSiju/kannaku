#!/usr/bin/env bash
# make demo-replay: the 5 demo cases and the app on recorded real Meta replies. No key, no model on this machine.
# Every answer says it is a replay. --check stops after the 5 cases (used by the fresh-clone test).
set -uo pipefail
source "$(dirname "$0")/lib.sh"
PORT="$(envget PORT 8013)"
[[ -x "$PY" ]] || "$ROOT/scripts/setup.sh" || exit 1
export LLM_PROVIDER=replay DB_PATH="$RUN_DIR/replay.db" KANAKKU_TOKEN=""
mkdir -p "$RUN_DIR"
rm -f "$RUN_DIR"/replay.db*
cd "$ROOT/server"
"$PY" -m app.db.seed_demo --reset >/dev/null || exit 1
"$PY" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --log-level warning &
server=$!
trap 'kill $server 2>/dev/null' EXIT
for _ in $(seq 1 60); do curl -fs "http://127.0.0.1:$PORT/health" >/dev/null && break; sleep 0.5; done
"$PY" scripts/replay_check.py "http://127.0.0.1:$PORT" || exit 1
[[ "${1:-}" == --check ]] && exit 0
# a fresh family for the app: the 5 cases above were only the check
"$PY" scripts/replay_check.py --reset-note
echo
echo "Replay is serving the app at http://$(lan_ip 2>/dev/null || hostname -I | awk '{print $1}'):$PORT (no token). Ctrl+C stops it."
wait "$server"
