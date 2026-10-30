-- Kanakku SQLite schema. Idempotent (CREATE ... IF NOT EXISTS).
-- Unknown profile values have NO row. Every confirmed value keeps its source.
-- Never stored: Aadhaar, PAN, account numbers (stripped by repo.strip_ids before any write).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS family (
    id            INTEGER PRIMARY KEY,
    language      TEXT NOT NULL DEFAULT 'en',
    guardian_code TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS member (
    id        INTEGER PRIMARY KEY,
    family_id INTEGER NOT NULL REFERENCES family(id) ON DELETE CASCADE,
    name      TEXT NOT NULL,
    role      TEXT NOT NULL CHECK (role IN ('primary', 'guardian', 'other'))
);

CREATE TABLE IF NOT EXISTS profile_value (
    id         INTEGER PRIMARY KEY,
    member_id  INTEGER NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    field      TEXT NOT NULL,
    value      REAL NOT NULL,
    unit       TEXT NOT NULL DEFAULT 'INR',
    source     TEXT NOT NULL CHECK (source IN ('typed', 'voice', 'document')),
    source_ref TEXT,
    confirmed  INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (member_id, field)
);

CREATE TABLE IF NOT EXISTS family_item (
    id         INTEGER PRIMARY KEY,
    family_id  INTEGER NOT NULL REFERENCES family(id) ON DELETE CASCADE,
    kind       TEXT NOT NULL CHECK (kind IN ('policy', 'loan', 'deposit', 'chit', 'other')),
    name       TEXT NOT NULL,
    amount     REAL NOT NULL,
    frequency  TEXT NOT NULL CHECK (frequency IN ('monthly', 'yearly', 'once')),
    start_date TEXT,
    end_date   TEXT,
    source     TEXT NOT NULL CHECK (source IN ('typed', 'voice', 'document')),
    source_ref TEXT,
    confirmed  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS "case" (
    id           INTEGER PRIMARY KEY,
    family_id    INTEGER NOT NULL REFERENCES family(id) ON DELETE CASCADE,
    case_type    TEXT,
    status       TEXT NOT NULL DEFAULT 'open',
    transcript   TEXT,
    language     TEXT,
    privacy_mode TEXT NOT NULL DEFAULT 'discreet' CHECK (privacy_mode IN ('full', 'discreet')),
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- quote_id = 'q' || evidence.id  (see repo.quote_id)
CREATE TABLE IF NOT EXISTS evidence (
    id      INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    source  TEXT NOT NULL,          -- 'transcript' | 'page_N'
    text    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS term (
    id          INTEGER PRIMARY KEY,
    case_id     INTEGER NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    value       REAL,
    unit        TEXT,
    evidence_id INTEGER REFERENCES evidence(id),
    verified    INTEGER NOT NULL DEFAULT 0,
    reason      TEXT
);

CREATE TABLE IF NOT EXISTS fact (
    id          INTEGER PRIMARY KEY,
    case_id     INTEGER NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    fact_id     TEXT NOT NULL,
    label       TEXT NOT NULL,
    value       REAL,
    unit        TEXT NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('offer', 'personal')),
    formula     TEXT NOT NULL,
    inputs_json TEXT NOT NULL DEFAULT '{}',
    status      TEXT NOT NULL DEFAULT 'known',
    value_text  TEXT,
    UNIQUE (case_id, fact_id)
);

CREATE TABLE IF NOT EXISTS position (
    id       INTEGER PRIMARY KEY,
    case_id  INTEGER NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    agent    TEXT NOT NULL,
    round    INTEGER NOT NULL DEFAULT 1,
    stance   TEXT NOT NULL CHECK (stance IN ('for', 'against', 'unsure')),
    strength REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS argument (
    id             INTEGER PRIMARY KEY,
    case_id        INTEGER NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    agent          TEXT NOT NULL,
    round          INTEGER NOT NULL DEFAULT 1,
    text           TEXT NOT NULL,
    cited_ids_json TEXT NOT NULL DEFAULT '[]',
    kept           INTEGER NOT NULL,
    drop_reason    TEXT
);

CREATE TABLE IF NOT EXISTS verdict (
    id             INTEGER PRIMARY KEY,
    case_id        INTEGER NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    colour         TEXT NOT NULL CHECK (colour IN ('red', 'yellow', 'green')),
    score          REAL,
    disagreement   REAL,
    overrides_json TEXT NOT NULL DEFAULT '[]',
    sentence       TEXT,
    questions_json TEXT NOT NULL DEFAULT '[]',
    degraded       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS spoken_line (
    id             INTEGER PRIMARY KEY,
    case_id        INTEGER NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    speaker        TEXT NOT NULL,
    "order"        INTEGER NOT NULL,
    text           TEXT NOT NULL,
    allowed        INTEGER NOT NULL DEFAULT 1,
    blocked_reason TEXT
);

CREATE TABLE IF NOT EXISTS alert (
    id        INTEGER PRIMARY KEY,
    case_id   INTEGER NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    family_id INTEGER NOT NULL REFERENCES family(id) ON DELETE CASCADE,
    status    TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'handled')),
    note      TEXT
);

CREATE TABLE IF NOT EXISTS trace (
    id          INTEGER PRIMARY KEY,
    case_id     INTEGER NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
    step        TEXT NOT NULL,
    ms          REAL,
    outcome     TEXT,
    detail_json TEXT NOT NULL DEFAULT '{}'
);
