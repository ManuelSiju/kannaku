# Shared helpers for the ops scripts. Source it; do not run it.
# shellcheck shell=bash

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT/run"
PY="$ROOT/.venv/bin/python"

ENV_LOCAL="$ROOT/.env.local"  # secrets written by make up (gitignored, mode 600): META_API_KEY, KANAKKU_TOKEN

_fileget() {  # _fileget FILE KEY -> value (inline "# comments" and quotes stripped)
  [[ -f "$1" ]] || return 0
  grep -E "^$2=" "$1" | tail -n1 | cut -d= -f2- | sed -E 's/[[:space:]]+#.*$//; s/^[[:space:]]+|[[:space:]]+$//g; s/^"(.*)"$/\1/'
}

# envget KEY DEFAULT -> value from the environment, else .env.local, else .env, else DEFAULT.
envget() {
  local key="$1" default="${2:-}" val="${!1:-}"
  [[ -z "$val" ]] && val="$(_fileget "$ENV_LOCAL" "$key")"
  [[ -z "$val" ]] && val="$(_fileget "$ROOT/.env" "$key")"
  echo "${val:-$default}"
}

# envlocal_set KEY VALUE -> write KEY=VALUE to .env.local (created with mode 600; other lines kept).
envlocal_set() {
  local key="$1" val="$2" tmp
  ( umask 077; touch "$ENV_LOCAL" )
  chmod 600 "$ENV_LOCAL"
  tmp="$(umask 077; mktemp "$ENV_LOCAL.XXXXXX")"
  grep -vE "^$key=" "$ENV_LOCAL" >"$tmp" || true
  printf '%s=%s\n' "$key" "$val" >>"$tmp"
  mv "$tmp" "$ENV_LOCAL" && chmod 600 "$ENV_LOCAL"
}

# envlocal_del KEY -> remove KEY from .env.local. Returns 1 if it was not there.
envlocal_del() {
  local key="$1" tmp
  [[ -f "$ENV_LOCAL" ]] && grep -qE "^$key=" "$ENV_LOCAL" || return 1
  tmp="$(umask 077; mktemp "$ENV_LOCAL.XXXXXX")"
  grep -vE "^$key=" "$ENV_LOCAL" >"$tmp" || true
  mv "$tmp" "$ENV_LOCAL" && chmod 600 "$ENV_LOCAL"
}

interactive() { [[ -t 0 && -t 1 && -z "${CI:-}" ]]; }

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
