#!/usr/bin/env bash
# make app-integration: the app's on-device tests against the REAL local server, with a screen recording.
#   1. stop the server, reset the demo family, start the server with the local models
#   2. record the emulator / phone screen (adb screenrecord, 3-minute segments) -> docs/demo_run.mp4
#   3. integration_test/demo_test.dart     (the whole demo path)
#   4. integration_test/failure_test.dart  (wrong token, oversized file, server stopped mid-ask)
# Needs: a booted emulator or a phone with USB debugging (adb devices), the local models (make llm-pull).
set -uo pipefail
source "$(dirname "$0")/lib.sh"

DEVICE="${DEVICE:-$(adb devices | awk 'NR>1 && $2=="device" {print $1; exit}')}"
[[ -n "$DEVICE" ]] || { echo "✘ no Android device: start an emulator or plug in a phone (make phone-devices)"; exit 1; }
PORT="$(envget PORT 8013)"
OUT="$ROOT/docs"
TMP="$RUN_DIR/integration"
rm -rf "$TMP" && mkdir -p "$TMP" "$OUT"
# An emulator reaches the laptop at 10.0.2.2; a phone over USB through adb reverse at 127.0.0.1.
if [[ "$DEVICE" == emulator-* ]]; then URL="http://10.0.2.2:$PORT"; else adb -s "$DEVICE" reverse "tcp:$PORT" "tcp:$PORT" >/dev/null; URL="http://127.0.0.1:$PORT"; fi

echo "== server: reset demo family, start with local models"
"$ROOT/scripts/down.sh" --server-only >/dev/null 2>&1
(cd "$ROOT/server" && "$PY" -m app.db.seed_demo --reset) || exit 1
PROVIDER=local "$ROOT/scripts/up.sh" </dev/null >"$TMP/up.log" 2>&1 || { tail -20 "$TMP/up.log"; exit 1; }
TOKEN="$(envget KANAKKU_TOKEN)"
DEFINES=(--dart-define=API_URL="$URL" --dart-define=API_TOKEN="$TOKEN")

echo "== recording the screen of $DEVICE"
record() {
  local i=0
  while [[ -f "$TMP/recording" ]]; do
    adb -s "$DEVICE" shell screenrecord --time-limit 175 --bit-rate 4000000 "/sdcard/kanakku_$i.mp4" 2>/dev/null
    echo "$i" >>"$TMP/segments"
    i=$((i + 1))
  done
}
touch "$TMP/recording"
record &
REC=$!

cd "$ROOT/app" || exit 1
echo "== demo path"
flutter test integration_test/demo_test.dart -d "$DEVICE" "${DEFINES[@]}" 2>&1 | tee "$TMP/demo_test.log" | grep -E "\[demo\]|All tests passed|Some tests failed|EXCEPTION|Expected|Actual"
DEMO=${PIPESTATUS[0]}

echo "== failure paths (the server is stopped as soon as the last ask reaches it)"
(
  start=$(wc -l <"$RUN_DIR/server.log")
  while true; do
    if tail -n +"$((start + 1))" "$RUN_DIR/server.log" | grep -q '"path": "/v1/cases".*"status": 202\|"status": 202.*"path": "/v1/cases"'; then
      sleep 2
      echo "[runner] stopping the server mid-ask"
      "$ROOT/scripts/down.sh" --server-only >/dev/null 2>&1
      break
    fi
    sleep 0.5
  done
) &
WATCH=$!
flutter test integration_test/failure_test.dart -d "$DEVICE" "${DEFINES[@]}" 2>&1 | tee "$TMP/failure_test.log" | grep -E "\[demo\]|\[runner\]|All tests passed|Some tests failed|EXCEPTION|Expected|Actual"
FAIL=${PIPESTATUS[0]}
kill "$WATCH" 2>/dev/null

echo "== saving the recording"
rm -f "$TMP/recording"
adb -s "$DEVICE" shell pkill -INT screenrecord 2>/dev/null
wait "$REC" 2>/dev/null
: >"$TMP/list.txt"
for i in $(sort -n -u "$TMP/segments" 2>/dev/null); do
  adb -s "$DEVICE" pull "/sdcard/kanakku_$i.mp4" "$TMP/part_$i.mp4" >/dev/null 2>&1 && echo "file 'part_$i.mp4'" >>"$TMP/list.txt"
  adb -s "$DEVICE" shell rm -f "/sdcard/kanakku_$i.mp4"
done
if [[ -s "$TMP/list.txt" ]] && command -v ffmpeg >/dev/null; then
  (cd "$TMP" && ffmpeg -loglevel error -y -f concat -safe 0 -i list.txt -c copy "$OUT/demo_run.mp4") && echo "✔ docs/demo_run.mp4"
fi

"$ROOT/scripts/down.sh" --server-only >/dev/null 2>&1
echo
[[ $DEMO == 0 ]] && echo "✔ demo path passed" || echo "✘ demo path failed (run/integration/demo_test.log)"
[[ $FAIL == 0 ]] && echo "✔ failure paths passed" || echo "✘ failure paths failed (run/integration/failure_test.log)"
[[ $DEMO == 0 && $FAIL == 0 ]]
