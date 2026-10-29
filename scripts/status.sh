#!/usr/bin/env bash
# make status: what is running, on which ports, and is it healthy.
set -uo pipefail
source "$(dirname "$0")/lib.sh"

PORT="$(envget PORT 8013)"
LLM_BASE_URL="$(envget LLM_BASE_URL http://localhost:11434/v1)"

if alive "$RUN_DIR/server.pid" "uvicorn app.main:app"; then
  echo "server   ✔ running  pid $(cat "$RUN_DIR/server.pid")  port $PORT"
elif ss -ltn "sport = :$PORT" 2>/dev/null | grep -q LISTEN; then
  echo "server   ? port $PORT in use, but not by make up"
else
  echo "server   ✘ stopped"
fi
if http_ok "http://127.0.0.1:$PORT/health"; then
  echo "health   ✔ http://127.0.0.1:$PORT/health"
  curl -fsS "http://127.0.0.1:$PORT/health" | "$PY" -c '
import json, sys
for k, v in json.load(sys.stdin)["providers"].items():
    print("           %s %-4s %s  %s" % ("✔" if v["reachable"] else "✘", k, v["provider"], v.get("error", "")))'
else
  echo "health   ✘ no answer on :$PORT"
fi
if http_ok "$LLM_BASE_URL/models"; then
  owner="external"; alive "$RUN_DIR/llm.pid" "" && owner="started by make up, pid $(cat "$RUN_DIR/llm.pid")"
  echo "llm      ✔ $LLM_BASE_URL ($owner)"
else
  echo "llm      ✘ $LLM_BASE_URL not answering"
fi
echo "phone    http://$(lan_ip):$PORT"
