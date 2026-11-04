-- Every paper a family showed, with the category it was given. One row per family and file (by content hash), so
-- follow-ups and later sessions know what a paper is, and a re-sent paper keeps its category.
CREATE TABLE IF NOT EXISTS document (
    id         INTEGER PRIMARY KEY,
    family_id  INTEGER NOT NULL REFERENCES family(id) ON DELETE CASCADE,
    case_id    INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,  -- the case that last categorised it
    filename   TEXT NOT NULL,
    sha256     TEXT NOT NULL,
    doc_type   TEXT NOT NULL DEFAULT 'unknown',
    terms_json TEXT NOT NULL DEFAULT '{}',                               -- verified terms: name -> as shown
    times_seen INTEGER NOT NULL DEFAULT 1,
    first_seen TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (family_id, sha256)
);
CREATE INDEX IF NOT EXISTS document_case ON document (case_id);
