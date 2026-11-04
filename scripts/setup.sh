#!/usr/bin/env bash
# Auto-setup, run by make start. Does nothing (and takes well under 2 s) when nothing changed:
#   settings file, uv, Python packages (stamp in run/ holds the hash of server/pyproject.toml), system packages.
# The local AI model is handled by up.sh, because it is only needed when the local models are chosen.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$RUN_DIR"
STAMP="$RUN_DIR/setup.stamp"
SYS_STAMP="$RUN_DIR/system.declined"

[[ -f "$ROOT/.env" ]] || { cp "$ROOT/.env.example" "$ROOT/.env"; echo "✔ Settings file created"; }

# ---------------------------------------------------------------- Python packages
want="$(sha256sum "$ROOT/server/pyproject.toml" | cut -d' ' -f1)"
if [[ ! -x "$PY" || "$(cat "$STAMP" 2>/dev/null)" != "$want" ]]; then
  echo "Setting up Kanakku's server parts (the first time takes a few minutes)…"
  if ! command -v uv >/dev/null; then
    echo "Installing uv, which installs Python for Kanakku…"
    curl -LsSf https://astral.sh/uv/install.sh | sh || { echo "✘ Could not install uv. Check the internet and try again."; exit 1; }
  fi
  [[ -x "$PY" ]] || uv venv -q --python 3.11 "$ROOT/.venv" || { echo "✘ Could not set up Python. Run: make doctor"; exit 1; }
  uv pip install -q --python "$PY" -e "$ROOT/server[dev]" || { echo "✘ Could not install the server parts. Check the internet and try again."; exit 1; }
  echo "$want" >"$STAMP"
  echo "✔ Server parts ready"
fi

# ---------------------------------------------------------------- system packages
missing=()
command -v tesseract >/dev/null || missing+=(tesseract-ocr tesseract-ocr-eng)
command -v ffmpeg >/dev/null || missing+=(ffmpeg)
command -v adb >/dev/null || missing+=(adb)
if command -v tesseract >/dev/null; then
  langs=" $(tesseract --list-langs 2>/dev/null | tail -n +2 | tr '\n' ' ')"
  [[ "$langs" == *" eng "* ]] || missing+=(tesseract-ocr-eng)
  [[ "$langs" == *" mal "* ]] || missing+=(tesseract-ocr-mal)
fi
if (( ${#missing[@]} )); then
  key="${missing[*]}"
  if [[ "$(cat "$SYS_STAMP" 2>/dev/null)" != "$key" ]]; then  # a refused install is not asked again until the list changes
    echo "Kanakku needs to install system packages; you may be asked for your password once."
    echo "  (${missing[*]})"
    if interactive; then sudo apt-get update -qq && sudo apt-get install -y -qq "${missing[@]}"; else sudo -n apt-get install -y -qq "${missing[@]}"; fi
    if [[ $? == 0 ]]; then
      rm -f "$SYS_STAMP"; echo "✔ System packages installed"
    else
      echo "$key" >"$SYS_STAMP"
      echo "! Not installed. Run make doctor to see what this affects."
    fi
  fi
  # Malayalam is optional; everything else is needed
  if ! command -v tesseract >/dev/null || ! command -v ffmpeg >/dev/null; then
    rm -f "$SYS_STAMP"
    echo "✘ Kanakku cannot start without these. Run make start again and type your password when asked."
    exit 1
  fi
fi
exit 0
