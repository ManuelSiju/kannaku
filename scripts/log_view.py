#!/usr/bin/env python3
"""Follows run/server.log (JSON lines) and prints one readable line each: time, level, request id, message.
Colours only on a real terminal. Survives log rotation. Standard library only."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

COLOURS = {"WARNING": "\033[33m", "ERROR": "\033[31m", "CRITICAL": "\033[31m", "DEBUG": "\033[2m"}
RESET, DIM = "\033[0m", "\033[2m"


def line(raw: str, colour: bool) -> str:
    try:
        r = json.loads(raw)
    except ValueError:
        return raw.rstrip()
    ts = str(r.get("ts", ""))[11:19]
    level, rid = str(r.get("level", "")), str(r.get("request_id", ""))[:8]
    msg = str(r.get("msg", ""))
    if "ms" in r:
        msg += f"  ({r['ms']:.0f} ms)"
    if colour:
        c = COLOURS.get(level, "")
        return f"{DIM}{ts}{RESET} {c}{level:<7}{RESET} {DIM}{rid:<8}{RESET} {c}{msg}{RESET if c else ''}"
    return f"{ts} {level:<7} {rid:<8} {msg}"


def follow(path: Path) -> None:
    colour = sys.stdout.isatty() and os.environ.get("TERM", "dumb") != "dumb" and "NO_COLOR" not in os.environ
    while not path.exists():
        time.sleep(0.2)
    f = path.open(encoding="utf-8", errors="replace")
    f.seek(0, os.SEEK_END)
    inode = os.fstat(f.fileno()).st_ino
    while True:
        raw = f.readline()
        if raw:
            print(line(raw, colour), flush=True)
            continue
        time.sleep(0.3)
        try:
            if path.stat().st_ino != inode:  # rotated
                f.close()
                f = path.open(encoding="utf-8", errors="replace")
                inode = os.fstat(f.fileno()).st_ino
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    try:
        follow(Path(sys.argv[1]))
    except (KeyboardInterrupt, BrokenPipeError):
        pass
