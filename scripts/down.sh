#!/usr/bin/env bash
# make down: stop the server, and the LLM backend ONLY if make up started it. Safe to run twice.
#   --server-only: leave the LLM backend running (used by make smoke).
set -uo pipefail
source "$(dirname "$0")/lib.sh"

echo "Stopping Kanakku"
if [[ -f "$RUN_DIR/server.pid" ]]; then stop_pid "$RUN_DIR/server.pid" server; else echo "  server not started by make up"; fi
if [[ "${1:-}" == --server-only ]]; then
  :
elif [[ -f "$RUN_DIR/llm.pid" ]]; then
  stop_pid "$RUN_DIR/llm.pid" "LLM backend"
else
  echo "  LLM backend left alone (not started by make up)"
fi
