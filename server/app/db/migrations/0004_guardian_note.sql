-- The guardian's note for Amma is kept apart from the alert's own message (alert.note).
ALTER TABLE alert ADD COLUMN guardian_note TEXT;
ALTER TABLE alert ADD COLUMN noted_at TEXT;
