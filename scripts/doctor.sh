#!/usr/bin/env bash
# make doctor: checks everything Kanakku needs and prints one line each, in plain words:
#   ✔ OK   ✘ PROBLEM (and the exact command that fixes it)   · optional (nice to have)
set -uo pipefail
source "$(dirname "$0")/lib.sh"

PORT="$(envget PORT 8013)"
LLM_BASE_URL="$(envget LLM_BASE_URL http://localhost:11434/v1)"
LLM_MODEL="$(envget LLM_MODEL qwen2.5:7b-instruct)"
problems=0
ok()   { printf "  ✔ %-22s %s\n" "$1" "$2"; }
bad()  { printf "  ✘ %-22s %s\n      → %s\n" "$1" "$2" "$3"; problems=$((problems + 1)); }
opt()  { printf "  · %-22s %s\n      → %s\n" "$1" "$2" "$3"; }

echo "Kanakku check-up"
echo

# ---------------------------------------------------------------- laptop tools
if [[ -x "$PY" ]]; then ok "Python" "$("$PY" --version 2>&1) in .venv"; else bad "Python" "the project is not set up yet" "make start"; fi
if [[ -x "$PY" ]] && "$PY" -c "import fastapi, openai, faster_whisper" 2>/dev/null; then ok "Server parts" "installed"
elif [[ -x "$PY" ]]; then bad "Server parts" "some are missing" "make start"; fi
command -v uv >/dev/null && ok "uv" "installed" || bad "uv" "not installed (it installs Python for you)" "curl -LsSf https://astral.sh/uv/install.sh | sh"
[[ -f "$ROOT/.env" ]] && ok "Settings file (.env)" "present" || bad "Settings file (.env)" "missing" "make start"

if command -v ollama >/dev/null; then
  ok "Ollama" "installed"
  if http_ok "$LLM_BASE_URL/models"; then
    if curl -fsS --max-time 5 "$LLM_BASE_URL/models" | grep -q "\"$LLM_MODEL\""; then ok "Local model" "$LLM_MODEL is ready"
    else ok "Local model" "$LLM_MODEL not downloaded yet (make start downloads it, about 4.7 GB)"; fi
  elif url_frozen "$LLM_BASE_URL"; then
    bad "Local AI (Ollama)" "frozen: it holds its port but does not answer (this happens after Ctrl+Z)" "killall -9 ollama"
  else
    ok "Local model" "Ollama is not running now (make start starts it)"
  fi
else
  bad "Ollama" "not installed (runs the AI on this laptop)" "curl -fsSL https://ollama.com/install.sh | sh"
fi

if command -v tesseract >/dev/null; then
  langs="$(tesseract --list-langs 2>/dev/null | tail -n +2 | tr '\n' ' ')"
  [[ " $langs " == *" eng "* ]] && ok "Reading photos (OCR)" "English ready" || bad "Reading photos (OCR)" "English pack missing" "make start"
  [[ " $langs " == *" mal "* ]] && ok "Malayalam papers" "ready" || opt "Malayalam papers" "not installed (only for photos of Malayalam papers)" "sudo apt install tesseract-ocr-mal"
else
  bad "Reading photos (OCR)" "Tesseract is not installed" "make start"
fi
command -v ffmpeg >/dev/null && ok "Audio tools (ffmpeg)" "installed" || bad "Audio tools (ffmpeg)" "not installed" "make start"

free_gb=$(df -Pk "$ROOT" | awk 'NR==2 {print int($4/1024/1024)}')
if (( free_gb >= 10 )); then ok "Disk space" "${free_gb} GB free"; else bad "Disk space" "only ${free_gb} GB free (need 10 GB)" "delete some large files, then run make doctor again"; fi

# ---------------------------------------------------------------- phone tools
if command -v flutter >/dev/null; then ok "Flutter" "installed (builds the phone app)"
else bad "Flutter" "not installed (needed once, to build the phone app)" "see docs/OWNER_GUIDE.md, section 4"; fi
if command -v adb >/dev/null; then
  ok "adb" "installed (puts the app on the phone)"
  phones="$(adb devices 2>/dev/null | awk 'NR>1 && $2=="device" {print $1}' | tr '\n' ' ')"
  unauth="$(adb devices 2>/dev/null | awk 'NR>1 && $2=="unauthorized"' | wc -l)"
  if [[ -n "$phones" ]]; then ok "Phone by USB" "connected: $phones"
  elif (( unauth > 0 )); then opt "Phone by USB" "connected but not allowed yet" "unlock the phone and tap Allow on the 'USB debugging' question"
  else opt "Phone by USB" "none connected (only needed for make phone)" "plug in the phone with USB debugging on (docs/OWNER_GUIDE.md, section 4)"; fi
else
  bad "adb" "not installed (puts the app on the phone)" "sudo apt install adb"
fi

# ---------------------------------------------------------------- running state
if [[ -f "$ENV_LOCAL" ]] && grep -q '^KANAKKU_TOKEN=' "$ENV_LOCAL"; then ok "Phone code (token)" "saved in .env.local"
else ok "Phone code (token)" "not made yet (make start makes it)"; fi
if [[ -f "$ENV_LOCAL" && "$(stat -c %a "$ENV_LOCAL")" != "600" ]]; then bad ".env.local" "other users can read it" "chmod 600 .env.local"; fi
if alive "$RUN_DIR/server.pid" "uvicorn app.main:app"; then
  if http_ok "http://127.0.0.1:$PORT/health"; then ok "Kanakku server" "running: http://$(lan_ip):$PORT"
  else bad "Kanakku server" "started but not answering" "make stop, then make start"; fi
elif ss -ltn "sport = :$PORT" 2>/dev/null | grep -q LISTEN; then
  bad "Port $PORT" "used by another program" "close that program, or set PORT=8014 in .env"
else
  ok "Kanakku server" "stopped (make start starts it); port $PORT is free"
fi
[[ -n "$(lan_ip)" ]] && ok "Wi-Fi address" "$(lan_ip)" || bad "Wi-Fi address" "this laptop is not on a network" "connect to Wi-Fi"

echo
if (( problems == 0 )); then
  echo "All good. Next: make start"
else
  echo "$problems problem(s). Run the command under each ✘, then run make doctor again."
fi
(( problems == 0 ))
