#!/usr/bin/env bash
# make app-release / make app-ios: bump version, build, archive to dist/, install on a connected phone.
#   usage: app_release.sh android|ios   (env: BUMP=build|patch|minor, API_URL=...)
set -uo pipefail
source "$(dirname "$0")/lib.sh"

TARGET="${1:-android}"
BUMP="${BUMP:-build}"
APP="$ROOT/app"
PUBSPEC="$APP/pubspec.yaml"
DIST="$ROOT/dist"

if [[ ! -f "$PUBSPEC" ]]; then
  echo "Flutter app not created yet (phase 5)"
  exit 0
fi
if [[ "$TARGET" == ios && "$(uname)" != Darwin ]]; then
  echo "iOS builds need a Mac with Xcode and Apple signing; run make app-ios on macOS."
  exit 0
fi
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
if [[ "$TARGET" == ios ]]; then
  flutter build ipa --release --dart-define=API_URL="$API_URL" || revert "flutter build ipa failed"
  ARTIFACT="$(ls -t build/ios/ipa/*.ipa 2>/dev/null | head -n1)"
  EXT=ipa
else
  if [[ -f android/key.properties ]]; then echo "Signing with android/key.properties"; else echo "Signing: debug key (no android/key.properties)"; fi
  flutter build apk --release --dart-define=API_URL="$API_URL" || revert "flutter build apk failed"
  ARTIFACT="build/app/outputs/flutter-apk/app-release.apk"
  EXT=apk
fi
[[ -f "$ARTIFACT" ]] || revert "build output not found"

# ---------------------------------------------------------------- commit + archive
git -C "$ROOT" commit -q -m "release: v$VERSION" -- "$PUBSPEC" || revert "could not commit version bump"
SHA="$(git -C "$ROOT" rev-parse --short HEAD)"
mkdir -p "$DIST"
OUT="$DIST/kanakku-v$VERSION-$SHA.$EXT"
cp "$ARTIFACT" "$OUT"
[[ -f "$DIST/RELEASES.md" ]] || printf '# Kanakku releases\n\n| version | date | git sha | platform | API_URL |\n|---|---|---|---|---|\n' >"$DIST/RELEASES.md"
echo "| v$VERSION | $(date +%F) | $SHA | $TARGET | $API_URL |" >>"$DIST/RELEASES.md"
echo "✔ $OUT"

# ---------------------------------------------------------------- install
if [[ "$TARGET" == android ]]; then
  if command -v adb >/dev/null && adb devices | awk 'NR>1 && $2=="device"' | grep -q .; then
    adb install -r "$OUT" && echo "✔ installed on phone" || echo "✘ adb install failed"
  else
    echo "No phone connected. Install later with: adb install -r $OUT"
  fi
fi
