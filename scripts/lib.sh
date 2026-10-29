# Shared helpers for the ops scripts. Source it; do not run it.
# shellcheck shell=bash

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT/run"
PY="$ROOT/.venv/bin/python"

# envget KEY DEFAULT -> value from the environment, else .env (inline "# comments" stripped), else DEFAULT.
envget() {
  local key="$1" default="${2:-}" val="${!1:-}"
  if [[ -z "$val" && -f "$ROOT/.env" ]]; then
    val="$(grep -E "^${key}=" "$ROOT/.env" | tail -n1 | cut -d= -f2- | sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+|[[:space:]]+$//g; s/^"(.*)"$/\1/')"
  fi
  echo "${val:-$default}"
}

lan_ip() {
  ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}'
}

# alive PIDFILE PATTERN -> 0 if the pid in PIDFILE is running AND its command line matches PATTERN
# (guards against a stale pid file pointing at a recycled pid).
alive() {
  local pidfile="$1" pattern="$2" pid
  [[ -f "$pidfile" ]] || return 1
  pid="$(cat "$pidfile" 2>/dev/null)"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null || return 1
  tr '\0' ' ' <"/proc/$pid/cmdline" 2>/dev/null | grep -q -- "$pattern"
}

# stop_pid PIDFILE NAME -> SIGTERM, wait up to 10 s, then SIGKILL. Removes the pid file. Safe if absent.
stop_pid() {
  local pidfile="$1" name="$2" pid
  if [[ ! -f "$pidfile" ]]; then return 0; fi
  pid="$(cat "$pidfile" 2>/dev/null)"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    # Signal the whole process group (launch() makes the process a group leader), so children go too.
    kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null
    for _ in $(seq 1 20); do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
    if kill -0 "$pid" 2>/dev/null; then
      echo "  $name did not stop in 10 s; sending SIGKILL"
      kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null
    fi
    echo "  ✔ stopped $name (pid $pid)"
  else
    echo "  $name was not running (stale pid file removed)"
  fi
  rm -f "$pidfile"
}

# launch PIDFILE LOGFILE CMD... -> start CMD detached in its own session; the process itself writes PIDFILE
# (setsid may fork, so $! would be the wrong pid). Waits until the pid file exists.
launch() {
  local pidfile="$1" logfile="$2"; shift 2
  rm -f "$pidfile"
  setsid bash -c 'echo $$ >"$0"; exec "$@"' "$pidfile" "$@" >"$logfile" 2>&1 </dev/null &
  for _ in $(seq 1 50); do [[ -s "$pidfile" ]] && return 0; sleep 0.1; done
  return 1
}

http_ok() { curl -fsS -o /dev/null --max-time 2 "$1" 2>/dev/null; }
