#!/usr/bin/env bash
# make demo-replay: the 5 demo cases and the app on recorded real Meta replies. No key, no model on this machine.
# Every answer says it is a replay. --check stops after the 5 cases (used by the fresh-clone test).
set -uo pipefail
source "$(dirname "$0")/lib.sh"
PORT="$(envget PORT 8013)"
[[ -x "$PY" ]] || "$ROOT/scripts/setup.sh" || exit 1
export LLM_PROVIDER=replay DB_PATH="$RUN_DIR/replay.db" KANAKKU_TOKEN=replay-demo  # only serves recorded replies
mkdir -p "$RUN_DIR"
rm -f "$RUN_DIR"/replay.db*
cd "$ROOT/server"
serve() {
  "$PY" -m app.db.seed_demo --reset >/dev/null || exit 1
  "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --log-level warning >>"$RUN_DIR/replay.log" 2>&1 &
  server=$!
  for _ in $(seq 1 60); do curl -fs "http://127.0.0.1:$PORT/health" >/dev/null && return; sleep 0.5; done
  echo "✘ The server did not start. See run/replay.log"; exit 1
}
trap 'kill $server 2>/dev/null' EXIT
serve
"$PY" scripts/replay_check.py "http://127.0.0.1:$PORT" || exit 1
[[ "${1:-}" == --check ]] && exit 0
# the app starts from a fresh family: the 5 cases above were only the check
kill "$server"; wait "$server" 2>/dev/null
rm -f "$RUN_DIR"/replay.db*
serve
ip="$(lan_ip)"
echo
KANAKKU_URL="http://$ip:$PORT" "$PY" scripts/print_qr.py 2>/dev/null
cat <<BOX

  Replay is running. No key is needed, and every answer says it is a replay.

  On your phone: open Kanakku, Settings, Scan code, and point it at the square above.
  Or type these in Settings, then tap "Save and test connection":
    Server address:   http://$ip:$PORT
    Access token:     $KANAKKU_TOKEN

  Same Wi-Fi as this laptop. If the phone cannot connect, run: make firewall-open

  Ask the demo questions from the README. Anything else is outside the recording and says so.
  Ctrl+C stops it.
BOX
wait "$server"
