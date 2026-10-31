#!/usr/bin/env bash
# make forget-key: delete the saved Meta key from .env.local.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
if envlocal_del META_API_KEY; then
  echo "✔ Meta key removed from .env.local (a running server keeps it until make down)"
else
  echo "no saved Meta key in .env.local"
fi
[[ -n "${META_API_KEY:-}" ]] && echo "! META_API_KEY is still set in your shell environment: unset META_API_KEY"
exit 0
