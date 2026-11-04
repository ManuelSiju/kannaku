#!/usr/bin/env bash
# make app-release: bump version, build the Android APK, archive to dist/, install on a connected phone.
#   env: BUMP=build|patch|minor, API_URL=...
set -uo pipefail
source "$(dirname "$0")/lib.sh"

BUMP="${BUMP:-build}"
APP="$ROOT/app"
PUBSPEC="$APP/pubspec.yaml"
DIST="$ROOT/dist"

command -v flutter >/dev/null || { echo "✘ flutter not on PATH"; exit 1; }

API_URL="${API_URL:-http://$(lan_ip):$(envget PORT 8013)}"

# ---------------------------------------------------------------- version bump
current="$(grep -E '^version:' "$PUBSPEC" | head -n1 | awk '{print $2}')"
[[ "$current" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)\+([0-9]+)$ ]] || {
  echo "✘ pubspec version '$current' is not X.Y.Z+N"; exit 1; }
X=${BASH_REMATCH[1]} Y=${BASH_REMATCH[2]} Z=${BASH_REMATCH[3]} N=${BASH_REMATCH[4]}
case "$BUMP" in
  build) ;;
  patch) Z=$((Z + 1)) ;;
  minor) Y=$((Y + 1)); Z=0 ;;
  *) echo "✘ BUMP must be build, patch or minor"; exit 1 ;;
esac
N=$((N + 1))
VERSION="$X.$Y.$Z+$N"
sed -i.bak -E "s/^version:.*/version: $VERSION/" "$PUBSPEC" && rm -f "$PUBSPEC.bak"
echo "Version $current -> $VERSION   (API_URL baked in: $API_URL)"

revert() { echo "✘ $*"; git -C "$ROOT" checkout -- "$PUBSPEC"; exit 1; }

# ---------------------------------------------------------------- build
cd "$APP" || exit 1
# The test-only integration_test plugin does not compile in release mode, and an editor running pub get keeps it in the
# generated plugin list. So it leaves pubspec.yaml for the build and comes back right after.
cp pubspec.yaml "$RUN_DIR/pubspec.full"
sed -i '/^  integration_test:$/,+1d' pubspec.yaml
restore_tests() { cp "$RUN_DIR/pubspec.full" pubspec.yaml; git -C "$ROOT" checkout -- app/pubspec.lock; flutter pub get >/dev/null; }
flutter pub get >/dev/null || { restore_tests; revert "flutter pub get failed"; }
if [[ -f android/key.properties ]]; then echo "Signing with android/key.properties"; else echo "Signing: debug key (no android/key.properties)"; fi
flutter build apk --release --dart-define=API_URL="$API_URL" || { restore_tests; revert "flutter build apk failed"; }
restore_tests
ARTIFACT="build/app/outputs/flutter-apk/app-release.apk"
[[ -f "$ARTIFACT" ]] || revert "build output not found"

# ---------------------------------------------------------------- commit + archive
git -C "$ROOT" commit -q -m "release: v$VERSION" -- "$PUBSPEC" || revert "could not commit version bump"
SHA="$(git -C "$ROOT" rev-parse --short HEAD)"
mkdir -p "$DIST"
OUT="$DIST/kanakku-v$VERSION-$SHA.apk"
cp "$ARTIFACT" "$OUT"
[[ -f "$DIST/RELEASES.md" ]] || printf '# Kanakku releases\n\n| version | date | git sha | platform | API_URL |\n|---|---|---|---|---|\n' >"$DIST/RELEASES.md"
echo "| v$VERSION | $(date +%F) | $SHA | android | $API_URL |" >>"$DIST/RELEASES.md"
echo "✔ $OUT"

# ---------------------------------------------------------------- install
SERIAL="${DEVICE:-$(adb devices 2>/dev/null | awk 'NR>1 && $2=="device" {print $1}' | grep -v '^emulator-' | head -n1)}"
SERIAL="${SERIAL:-$(adb devices 2>/dev/null | awk 'NR>1 && $2=="device" {print $1}' | head -n1)}"
if [[ "${NO_INSTALL:-}" != 1 && -n "$SERIAL" ]]; then
  adb -s "$SERIAL" install -r "$OUT" && echo "✔ installed on $SERIAL" || echo "✘ adb install failed"
else
  echo "No phone connected. Install later with: adb install -r $OUT"
fi
