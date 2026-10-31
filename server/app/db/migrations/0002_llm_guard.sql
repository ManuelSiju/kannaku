-- Meta Model API spend guard: response cache and a per-day call counter.
CREATE TABLE IF NOT EXISTS llm_cache (
    key        TEXT PRIMARY KEY,             -- sha256 of (prompt, schema, model, images)
    model      TEXT NOT NULL,
    response   TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS llm_calls_daily (
    day   TEXT PRIMARY KEY,                  -- YYYY-MM-DD, local time
    calls INTEGER NOT NULL DEFAULT 0
);
