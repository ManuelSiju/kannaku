-- POST /cases with an Idempotency-Key: a resent request returns the first case instead of creating a new one.
CREATE TABLE IF NOT EXISTS idempotency (
    key        TEXT PRIMARY KEY,
    family_id  INTEGER NOT NULL,
    case_id    INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
