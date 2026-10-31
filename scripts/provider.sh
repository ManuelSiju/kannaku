#!/usr/bin/env bash
# make provider: the provider the running server uses, or what the next make up would choose. Never prints a key.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
PORT="$(envget PORT 8013)"
if http_ok "http://127.0.0.1:$PORT/health"; then
  curl -fsS --max-time 15 "http://127.0.0.1:$PORT/health" | "$PY" -c '
import json, sys
p = json.load(sys.stdin)["provider"]
g = p.get("spend_guard")
print("running  : %s  (model %s, cache %s)" % (p["name"], p["model"], "on" if p.get("cache") else "off"))
if g:
    print("spend    : %d / %d Meta calls today%s" % (g["calls_today"], g["cap"], "  (warning: over 80%)" if g["warning"] else ""))'
else
  echo "running  : none (server stopped)"
fi
if [[ -n "$(envget META_API_KEY)" ]]; then
  echo "next up  : meta (a saved META_API_KEY was found; make forget-key removes it)"
else
  echo "next up  : you will be asked for a Meta key (Enter = local); non-interactive = local"
fi
