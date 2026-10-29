#!/usr/bin/env bash
# make up: start LLM backend (if needed) + FastAPI server in the background. Idempotent.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
mkdir -p "$RUN_DIR"

HOST="$(envget HOST 0.0.0.0)"
PORT="$(envget PORT 8013)"
BACKEND="$(envget LLM_BACKEND ollama)"
LLM_BASE_URL="$(envget LLM_BASE_URL http://localhost:11434/v1)"
LLM_MODEL="$(envget LLM_MODEL qwen2.5:7b-instruct)"
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

[[ -x "$PY" ]] || fail "no .venv — run: make setup"

# ---------------------------------------------------------------- LLM backend
echo "LLM backend: $BACKEND  ($LLM_BASE_URL, model $LLM_MODEL)"
if http_ok "$LLM_BASE_URL/models"; then
  echo "  ✔ already running"
else
  case "$BACKEND" in
    ollama)
      command -v ollama >/dev/null || fail "ollama not installed (https://ollama.com/download)"
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
    echo "  model $LLM_MODEL missing — pulling"
    ollama pull "$LLM_MODEL" || fail "ollama pull $LLM_MODEL failed"
  else
    echo "  ! llama-server serves whatever LLAMA_MODEL_PATH points at; model name '$LLM_MODEL' is only a label"
  fi
else
  echo "  ✔ model $LLM_MODEL available"
fi

# ---------------------------------------------------------------- API server
echo "API server: $HOST:$PORT"
if alive "$SRV_PID" "uvicorn app.main:app"; then
  echo "  ✔ already running (pid $(cat "$SRV_PID")) — nothing to do"
else
  rm -f "$SRV_PID"
  if ss -ltn "sport = :$PORT" 2>/dev/null | grep -q LISTEN; then
    fail "port $PORT is already used by another process (ss -ltnp 'sport = :$PORT'); set PORT in .env"
  fi
  cd "$ROOT/server" || fail "no server/ directory"
  launch "$SRV_PID" "$RUN_DIR/server.log" "$PY" -m uvicorn app.main:app --host "$HOST" --port "$PORT" \
    || fail "could not start the server"
  cd "$ROOT" || exit 1
  STARTED_SRV=1
  echo -n "  starting (pid $(cat "$SRV_PID")) "
  for _ in $(seq 1 60); do
    http_ok "http://127.0.0.1:$PORT/health" && break
    alive "$SRV_PID" "uvicorn" || { echo; tail -n 20 "$RUN_DIR/server.log"; fail "server exited during start-up"; }
    echo -n "."; sleep 1
  done
  echo
  http_ok "http://127.0.0.1:$PORT/health" || fail "GET /health did not return 200 within 60 s (see run/server.log)"
  echo "  ✔ up"
fi

# ---------------------------------------------------------------- summary
trap - INT TERM
echo
echo "Providers:"
curl -fsS --max-time 10 "http://127.0.0.1:$PORT/health" | "$PY" -c '
import json, sys
for k, v in json.load(sys.stdin)["providers"].items():
    print("  %s %-4s %s  %s" % ("✔" if v["reachable"] else "✘", k, v["provider"], v.get("error", "")))'
echo
echo "Laptop : http://127.0.0.1:$PORT    (docs: /docs)"
echo "Phone  : http://$(lan_ip):$PORT    (same Wi-Fi; make firewall-open if blocked)"
echo "make down to stop"
