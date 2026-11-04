#!/usr/bin/env bash
# make phone: build the latest app and install it on the phone connected by USB; without a phone, print where the
# APK file is so it can be sent by WhatsApp / Google Drive and installed by hand. Also copies the demo brochure to
# the phone's Download folder.
set -uo pipefail
source "$(dirname "$0")/lib.sh"

mkdir -p "$RUN_DIR"
command -v flutter >/dev/null || { echo "✘ Flutter is not installed. See the Quick start in README.md."; exit 1; }
if [[ -n "$(git -C "$ROOT" status --porcelain -- app/pubspec.yaml)" ]]; then
  echo "✘ app/pubspec.yaml has unsaved changes; commit or undo them first (git -C app diff pubspec.yaml)."
  exit 1
fi

echo "Building the app (the first time takes about 5 minutes)…"
if ! NO_INSTALL=1 BUMP="${BUMP:-build}" "$ROOT/scripts/app_release.sh" >"$RUN_DIR/phone_build.log" 2>&1; then
  tail -n 15 "$RUN_DIR/phone_build.log"
  echo
  echo "✘ The app did not build. The details are in run/phone_build.log."
  exit 1
fi
APK="$(ls -t "$ROOT"/dist/kanakku-v*.apk | head -n1)"
echo "✔ App built: $APK"

# a real phone first, else an emulator
SERIAL="${DEVICE:-$(adb devices 2>/dev/null | awk 'NR>1 && $2=="device" {print $1}' | grep -v '^emulator-' | head -n1)}"
SERIAL="${SERIAL:-$(adb devices 2>/dev/null | awk 'NR>1 && $2=="device" {print $1}' | head -n1)}"
if [[ -n "$SERIAL" ]]; then
  if adb -s "$SERIAL" install -r "$APK" >/dev/null 2>&1; then
    echo "✔ Installed on the phone ($SERIAL). Open 'Kanakku' on the phone."
    adb -s "$SERIAL" push "$ROOT/server/demo_assets/kanakavalli_brochure.pdf" /sdcard/Download/ >/dev/null 2>&1 &&
      echo "✔ Demo brochure copied to the phone's Download folder (kanakavalli_brochure.pdf)."
  else
    echo "✘ Could not install on the phone. If an older Kanakku is installed from another laptop, uninstall it first."
  fi
else
  cat <<EOF

No phone is connected by USB. To install by hand:
  1. Send this file to the phone (WhatsApp to yourself, or Google Drive):
       $APK
  2. On the phone, tap the file and allow "Install unknown apps" when asked.
EOF
fi
