#!/usr/bin/env bash
# make up: choose the model provider, start the local LLM backend (only for local), then the FastAPI server in the
# background. Idempotent.
#
# Provider, in this order: PROVIDER=meta|local on the command line; else META_API_KEY (environment or .env.local)
# -> meta; else, in a terminal, ask once for a key (hidden; Enter = local); else (CI, make smoke) local.
# A Meta key is checked with one cheap call first; it is never printed or logged.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
mkdir -p "$RUN_DIR"

HOST="$(envget HOST 0.0.0.0)"
PORT="$(envget PORT 8013)"
BACKEND="$(envget LLM_BACKEND ollama)"
LLM_BASE_URL="$(envget LLM_BASE_URL http://localhost:11434/v1)"
LLM_MODEL="$(envget LLM_MODEL qwen2.5:7b-instruct)"
META_BASE_URL="$(envget META_BASE_URL https://api.meta.ai/v1)"
LLM_FALLBACK="$(envget LLM_FALLBACK none)"
LLM_PID="$RUN_DIR/llm.pid"
SRV_PID="$RUN_DIR/server.pid"
STARTED_LLM=0
STARTED_SRV=0

fail() {
  echo "✘ $*" >&2
  # Never leave half-started processes: undo only what THIS run started.
  [[ $STARTED_SRV == 1 ]] && stop_pid "$SRV_PID" server
  [[ $STARTED_LLM == 1 ]] && stop_pid "$LLM_PID" "LLM backend"
  exit 1
}
trap 'fail "interrupted"' INT TERM

[[ -x "$PY" ]] || fail "Kanakku is not set up yet — run: make start"

# ---------------------------------------------------------------- provider
PROVIDER="${PROVIDER:-}"
EXPLICIT="$PROVIDER"
KEY=""
KEY_SOURCE=""
case "$PROVIDER" in
  meta | local | "") ;;
  *) fail "PROVIDER must be meta or local (got '$PROVIDER')" ;;
esac
if [[ -z "$PROVIDER" || "$PROVIDER" == meta ]]; then
  KEY="$(envget META_API_KEY)"
  [[ -n "$KEY" ]] && KEY_SOURCE=saved
fi
if [[ -z "$PROVIDER" ]]; then
  if [[ -n "$KEY" ]]; then
    PROVIDER=meta
  elif interactive; then
    read -rs -p "Meta Model API key (press Enter to use the local models): " KEY
    echo
    if [[ -n "$KEY" ]]; then PROVIDER=meta; KEY_SOURCE=typed; else PROVIDER=local; fi
  else
    PROVIDER=local
  fi
elif [[ "$PROVIDER" == meta && -z "$KEY" ]]; then
  interactive || fail "PROVIDER=meta needs META_API_KEY (environment or .env.local)"
  read -rs -p "Meta Model API key: " KEY
  echo
  KEY_SOURCE=typed
  [[ -n "$KEY" ]] || fail "no key given"
fi

if [[ "$PROVIDER" == meta ]]; then
  echo -n "Checking the Meta key (one call, 10 s) ... "
  reason="$(META_API_KEY="$KEY" META_BASE_URL="$META_BASE_URL" "$PY" "$ROOT/server/scripts/meta_key.py")"
  rc=$?
  if [[ $rc == 0 ]]; then
    echo "✔ $reason"
  else
    echo "✘ $reason"
    if interactive; then
      read -r -p "Use local models instead? [Y/n] " ans
      [[ "${ans,,}" == n* ]] && fail "stopped. Fix the key (make forget-key forgets the saved one) and run make up again"
      PROVIDER=local; KEY=""; KEY_SOURCE=""
    elif [[ "$EXPLICIT" == meta ]]; then
      fail "PROVIDER=meta but the key check failed: $reason"
    else
      echo "  → using the local models instead"
      PROVIDER=local; KEY=""; KEY_SOURCE=""
    fi
  fi
fi
if [[ "$PROVIDER" == meta && "$KEY_SOURCE" == typed ]] && interactive; then
  read -r -p "Save this key for next time? [y/N] " ans
  if [[ "${ans,,}" == y* ]]; then
    envlocal_set META_API_KEY "$KEY" && echo "  ✔ saved in .env.local (readable only by you; make forget-key removes it)"
  fi
fi
echo "Provider: $PROVIDER"

# LAN access token for the phone app (generated once, kept in .env.local).
TOKEN="$(envget KANAKKU_TOKEN)"
if [[ -z "$TOKEN" ]]; then
  TOKEN="$("$PY" -c 'import secrets; print(secrets.token_urlsafe(18))')"
  envlocal_set KANAKKU_TOKEN "$TOKEN"
  echo "  ✔ new access token for the app saved in .env.local"
fi

# ---------------------------------------------------------------- local LLM backend (local provider only)
if [[ "$PROVIDER" == local ]]; then
  echo "LLM backend: $BACKEND  ($LLM_BASE_URL, model $LLM_MODEL)"
  if http_ok "$LLM_BASE_URL/models"; then
    echo "  ✔ already running"
  elif url_frozen "$LLM_BASE_URL"; then
    fail "the local AI (Ollama) is frozen: it holds its port but does not answer. This happens after Ctrl+Z.
  Fix it with:  killall -9 ollama
  Then run this command again. (To stop a command, use Ctrl+C, not Ctrl+Z.)"
  else
    case "$BACKEND" in
      ollama)
        if ! command -v ollama >/dev/null; then
          interactive || fail "Ollama is not installed (https://ollama.com/download)"
          echo "  Installing Ollama, which runs the AI on this laptop; you may be asked for your password once."
          curl -fsSL https://ollama.com/install.sh | sh || fail "could not install Ollama. Check the internet and try again"
        fi
        # Only when WE start Ollama: keep the text model and (if set) the vision model loaded together, never unload.
        # On an 8 GB GPU qwen2.5vl:7b does not fit next to the text model, so Ollama runs it on the CPU (slow);
        # vision calls then fall back to OCR text after LLM_VISION_TIMEOUT_S.
        export OLLAMA_MAX_LOADED_MODELS="${OLLAMA_MAX_LOADED_MODELS:-2}" OLLAMA_KEEP_ALIVE="${OLLAMA_KEEP_ALIVE:--1}"
        launch "$LLM_PID" "$RUN_DIR/llm.log" ollama serve || fail "could not start ollama"
        ;;
      llamacpp)
        command -v llama-server >/dev/null || fail "llama-server not on PATH (build llama.cpp)"
        MODEL_PATH="$(envget LLAMA_MODEL_PATH)"
        MMPROJ="$(envget LLAMA_MMPROJ_PATH)"
        [[ -f "$MODEL_PATH" ]] || fail "set LLAMA_MODEL_PATH in .env to your .gguf file"
        LLM_PORT="$(sed -E 's#.*:([0-9]+).*#\1#' <<<"$LLM_BASE_URL")"
        args=(-m "$MODEL_PATH" --host 127.0.0.1 --port "$LLM_PORT")
        [[ -n "$MMPROJ" ]] && args+=(--mmproj "$MMPROJ")
        launch "$LLM_PID" "$RUN_DIR/llm.log" llama-server "${args[@]}" || fail "could not start llama-server"
        ;;
      *) fail "LLM_BACKEND must be ollama or llamacpp (got '$BACKEND')" ;;
    esac
    STARTED_LLM=1
    echo -n "  starting (pid $(cat "$LLM_PID")) "
    for _ in $(seq 1 60); do http_ok "$LLM_BASE_URL/models" && break; echo -n "."; sleep 1; done
    echo
    http_ok "$LLM_BASE_URL/models" || fail "LLM endpoint did not answer within 60 s (see run/llm.log)"
    echo "  ✔ up"
  fi

  # Is the configured model there?
  if ! curl -fsS --max-time 5 "$LLM_BASE_URL/models" | "$PY" -c \
      'import json,sys; ids={m["id"] for m in json.load(sys.stdin).get("data",[])}; m=sys.argv[1]; sys.exit(0 if m in ids or m+":latest" in ids else 1)' \
      "$LLM_MODEL"; then
    if [[ "$BACKEND" == ollama ]]; then
      size=""; [[ "$LLM_MODEL" == qwen2.5:7b-instruct ]] && size=" (about 4.7 GB)"
      echo "  The AI model $LLM_MODEL is not on this laptop yet. Downloading it now$size…"
      ollama pull "$LLM_MODEL" || fail "ollama pull $LLM_MODEL failed"
    else
      echo "  ! llama-server serves whatever LLAMA_MODEL_PATH points at; model name '$LLM_MODEL' is only a label"
    fi
  else
    echo "  ✔ model $LLM_MODEL available"
  fi
else
  echo "LLM backend: Meta Model API (the local backend is not started)"
  if [[ "$LLM_FALLBACK" == local ]] && ! http_ok "$LLM_BASE_URL/models"; then
    echo "  ! LLM_FALLBACK=local, but the local models are not running: at the daily cap asks will fail (make llm-up)"
  fi
fi

# ---------------------------------------------------------------- API server
echo "API server: $HOST:$PORT"
if alive "$SRV_PID" "uvicorn app.main:app"; then
  running="$(curl -fsS --max-time 5 "http://127.0.0.1:$PORT/health" | "$PY" -c \
    'import json,sys; print(json.load(sys.stdin).get("provider",{}).get("name",""))' 2>/dev/null)"
  if [[ -n "$running" && "$running" != "$PROVIDER" ]]; then
    fail "the server is already running with provider '$running'. Run make down first, then make up again"
  fi
  echo "  ✔ already running (pid $(cat "$SRV_PID")) — nothing to do"
else
  rm -f "$SRV_PID"
  if ss -ltn "sport = :$PORT" 2>/dev/null | grep -q LISTEN; then
    fail "port $PORT is already used by another process (ss -ltnp 'sport = :$PORT'); set PORT in .env"
  fi
  cd "$ROOT/server" || fail "no server/ directory"
  # The key reaches the server through its environment only. JSON logs: run/server.log; console: run/server.out.
  export LLM_PROVIDER="$PROVIDER" KANAKKU_TOKEN="$TOKEN" LOG_PATH="${LOG_PATH:-$RUN_DIR/server.log}"
  export BACKUP_DIR="${BACKUP_DIR:-$RUN_DIR/backups}"
  if [[ "$PROVIDER" == meta ]]; then export META_API_KEY="$KEY"; fi
  launch "$SRV_PID" "$RUN_DIR/server.out" "$PY" -m uvicorn app.main:app --host "$HOST" --port "$PORT" \
    --timeout-graceful-shutdown 15 || fail "could not start the server"
  unset META_API_KEY
  cd "$ROOT" || exit 1
  STARTED_SRV=1
  echo -n "  starting (pid $(cat "$SRV_PID")) "
  for _ in $(seq 1 60); do
    http_ok "http://127.0.0.1:$PORT/health" && break
    alive "$SRV_PID" "uvicorn" || { echo; tail -n 20 "$RUN_DIR/server.out"; fail "server exited during start-up"; }
    echo -n "."; sleep 1
  done
  echo
  http_ok "http://127.0.0.1:$PORT/health" || fail "GET /health did not return 200 within 60 s (see run/server.out)"
  echo "  ✔ up"
fi

# ---------------------------------------------------------------- banner
trap - INT TERM
echo
curl -fsS --max-time 15 "http://127.0.0.1:$PORT/health" | "$PY" -c '
import json, sys
h = json.load(sys.stdin)
p = h.get("provider", {})
g = p.get("spend_guard")
print("Kanakku %s" % h.get("version", "?"))
print("  provider    : %s" % p.get("name"))
print("  model       : %s%s" % (p.get("model"), "   vision: %s" % p["vision_model"] if p.get("vision_model") else "   vision: off"))
print("  speech      : %s" % p.get("stt"))
print("  cache       : %s" % ("on" if p.get("cache") else "off"))
print("  spend guard : %s" % ("%d / %d calls today, fallback %s" % (g["calls_today"], g["cap"], p.get("fallback")) if g else "off (local)"))
for k, v in h["providers"].items():
    print("  %s %-4s %s  %s" % ("✔" if v["reachable"] else "✘", k, v["provider"], v.get("error", v.get("note", ""))))'
echo
echo "Laptop : http://127.0.0.1:$PORT    (docs: /docs)"
echo "Phone  : http://$(lan_ip):$PORT    (same Wi-Fi; make firewall-open if blocked)"
echo "Token  : $TOKEN    (app → Settings → Access token)"
echo "make stop to stop · make provider shows the provider · the log is in run/server.log"
