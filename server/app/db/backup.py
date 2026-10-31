"""Daily copy of the SQLite file into run/backups (keeps the newest N). Uses SQLite's online backup API, so it is
safe while the server is writing."""

from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path


def backup_daily(db_path: Path, backup_dir: Path, keep: int = 3, today: dt.date | None = None) -> Path | None:
    """Copy db_path to backup_dir/<stem>-YYYY-MM-DD.db once per day. Returns the new file, or None if today's copy
    already exists or there is no database yet."""
    if str(db_path) == ":memory:" or not Path(db_path).exists():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    day = (today or dt.date.today()).isoformat()
    target = backup_dir / f"{Path(db_path).stem}-{day}.db"
    made = None
    if not target.exists():
        src, dst = sqlite3.connect(db_path), sqlite3.connect(target)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        made = target
    old = sorted(backup_dir.glob(f"{Path(db_path).stem}-*.db"))
    for p in old[:-keep] if keep > 0 else old:
        p.unlink(missing_ok=True)
    return made
