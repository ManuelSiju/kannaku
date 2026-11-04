-- Whose money each value and item is, whether it counts in the family budget, and investment holdings.
-- family_item is rebuilt because SQLite cannot change a CHECK. Nothing references it, so the drop is safe.

ALTER TABLE profile_value ADD COLUMN in_household INTEGER NOT NULL DEFAULT 1;

CREATE TABLE family_item_new (
    id           INTEGER PRIMARY KEY,
    family_id    INTEGER NOT NULL REFERENCES family(id) ON DELETE CASCADE,
    member_id    INTEGER REFERENCES member(id) ON DELETE SET NULL,
    in_household INTEGER NOT NULL DEFAULT 1,
    kind         TEXT NOT NULL CHECK (kind IN ('policy', 'loan', 'deposit', 'chit', 'other',
                                               'mf_holding', 'stock_holding', 'sip')),
    name         TEXT NOT NULL,
    amount       REAL NOT NULL,
    frequency    TEXT NOT NULL CHECK (frequency IN ('monthly', 'yearly', 'once')),
    start_date   TEXT,
    end_date     TEXT,
    source       TEXT NOT NULL CHECK (source IN ('typed', 'voice', 'document')),
    source_ref   TEXT,
    confirmed    INTEGER NOT NULL DEFAULT 0,
    units        REAL,
    symbol       TEXT,
    scheme       TEXT,
    category     TEXT CHECK (category IN ('equity', 'debt', 'other'))
);

INSERT INTO family_item_new (id, family_id, kind, name, amount, frequency, start_date, end_date, source, source_ref,
                             confirmed)
SELECT id, family_id, kind, name, amount, frequency, start_date, end_date, source, source_ref, confirmed
FROM family_item;

DROP TABLE family_item;
ALTER TABLE family_item_new RENAME TO family_item;
