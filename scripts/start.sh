#!/usr/bin/env bash
# make start: auto-setup, Meta/local choice, start the AI and the server, USB tunnel, QR code and plain instructions,
# then the live log in this terminal. Ctrl+C (or closing the terminal) stops everything we started.
# BG=1: the old behaviour for developers: start in the background and return.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$RUN_DIR"
PORT="$(envget PORT 8013)"
START_PID="$RUN_DIR/start.pid"

box() {
  local token prov ip
  token="$(envget KANAKKU_TOKEN)"
  ip="$(lan_ip)"
  prov="$(curl -fsS --max-time 10 "http://127.0.0.1:$PORT/health" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["provider"]["name"])' 2>/dev/null)"
  echo
  KANAKKU_URL="http://$ip:$PORT" KANAKKU_TOKEN="$token" "$PY" "$ROOT/server/scripts/print_qr.py" 2>/dev/null
  cat <<BOX

  ╔══════════════════════════════════════════════════════════════╗
     Kanakku is running.   (AI: ${prov:-?})

     On your phone open the Kanakku app, go to Settings and tap
     "Scan code", then point the phone at the square above.

     Or type these in Settings:
       Server address:   http://$ip:$PORT
       Access token:     $token
     Then tap "Save and test connection".

     The phone must be on the same Wi-Fi as this laptop.
BOX
  [[ -s "$RUN_DIR/adb_reverse" ]] && echo "     Phone on the USB cable: http://127.0.0.1:$PORT also works."
  if [[ -z "${BG:-}" ]]; then
    echo "     To stop Kanakku: press Ctrl+C here."
  else
    echo "     To stop Kanakku: make stop"
  fi
  echo "  ╚══════════════════════════════════════════════════════════════╝"
  echo
}

# Already running in another terminal: show the settings, do not take it over.
if alive "$START_PID" "start.sh"; then
  echo "Kanakku is already running in another terminal window."
  box
  exit 0
fi

"$ROOT/scripts/setup.sh" || exit 1

fail_start() {
  echo
  echo "Kanakku did not start. Run: make doctor   (it says what to fix)"
  exit 1
}

reverse_tunnels() {
  : >"$RUN_DIR/adb_reverse"
  local serial
  for serial in $(phones_for_reverse); do
    adb -s "$serial" reverse "tcp:$PORT" "tcp:$PORT" >/dev/null 2>&1 && echo "$serial" >>"$RUN_DIR/adb_reverse"
  done
}

if [[ -n "${BG:-}" ]]; then
  PROVIDER="${PROVIDER:-}" "$ROOT/scripts/up.sh" || fail_start
  reverse_tunnels
  box
  exit 0
fi

# ---------------------------------------------------------------- foreground
echo $$ >"$START_PID"
VIEW=""
STOPPING=0
cleanup() {
  [[ $STOPPING == 1 ]] && return
  STOPPING=1
  trap '' INT TERM HUP PIPE               # a second Ctrl+C must not interrupt the clean-up
  [[ "${1:-}" == HUP ]] && exec >/dev/null 2>&1  # the terminal is gone: nothing to print to
  [[ -n "$VIEW" ]] && kill "$VIEW" 2>/dev/null
  echo
  echo "Stopping Kanakku…"
  "$ROOT/scripts/down.sh" >/dev/null 2>&1
  remove_reverse
  rm -f "$START_PID"
  echo "Kanakku stopped"
  exit 0
}
trap 'cleanup' INT TERM
trap 'cleanup HUP' HUP

if ! PROVIDER="${PROVIDER:-}" "$ROOT/scripts/up.sh"; then
  rm -f "$START_PID"
  fail_start
fi
reverse_tunnels
box
echo "Live log (time, level, request, message):"
"$PY" "$ROOT/scripts/log_view.py" "$RUN_DIR/server.log" &
VIEW=$!
while alive "$RUN_DIR/server.pid" "uvicorn app.main:app" || [[ -f "$RUN_DIR/demo.reset" ]]; do  # make demo restarts it
  sleep 1 &
  wait $!
done
echo
echo "✘ The server stopped by itself. The last lines are above; run make doctor."
cleanup
