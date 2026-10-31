#!/usr/bin/env bash
# make start: make up (asks for a Meta key, Enter = local models), then says in plain words what to do on the phone.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
PORT="$(envget PORT 8013)"

if ! PROVIDER="${PROVIDER:-}" "$ROOT/scripts/up.sh"; then
  echo
  echo "Kanakku did not start. Run: make doctor   (it says what to fix)"
  exit 1
fi
TOKEN="$(envget KANAKKU_TOKEN)"
PROV="$(curl -fsS --max-time 10 "http://127.0.0.1:$PORT/health" | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["provider"]["name"])' 2>/dev/null)"
cat <<EOF

  ╔══════════════════════════════════════════════════════════════╗
     Kanakku is running.   (AI: ${PROV:-?})

     On your phone open the Kanakku app.
     Settings → Server address:   http://$(lan_ip):$PORT
     Settings → Access token:     $TOKEN
     Then tap "Save and test connection".

     The phone must be on the same Wi-Fi as this laptop.
     To stop Kanakku later:  make stop
  ╚══════════════════════════════════════════════════════════════╝
EOF
