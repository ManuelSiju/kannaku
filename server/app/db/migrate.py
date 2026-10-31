"""Numbered SQL migrations (migrations/NNNN_name.sql), applied in order at start-up and recorded in schema_version.

0001 is the original schema (all CREATE ... IF NOT EXISTS), so databases created before migrations existed upgrade
cleanly. Never edit a migration that has shipped; add a new one.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

MIGRATIONS = Path(__file__).with_name("migrations")
_NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


def migrations() -> list[tuple[int, Path]]:
    found = [(int(m.group(1)), p) for p in MIGRATIONS.iterdir() if (m := _NAME.match(p.name))]
    found.sort()
    numbers = [n for n, _ in found]
    if numbers != list(range(1, len(numbers) + 1)):
        raise RuntimeError(f"migrations must be numbered 0001, 0002, ... without gaps (found {numbers})")
    return found


def current_version(conn: sqlite3.Connection) -> int:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version "
        "(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
    )
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return int(row[0] or 0)


def migrate(conn: sqlite3.Connection) -> list[int]:
    """Apply every migration newer than the database. Returns the versions applied."""
    done = current_version(conn)
    applied = []
    for n, path in migrations():
        if n <= done:
            continue
        conn.executescript(path.read_text())  # executescript commits first; each file is idempotent
        conn.execute("INSERT INTO schema_version (version, name) VALUES (?, ?)", (n, path.stem))
        conn.commit()
        applied.append(n)
    return applied
