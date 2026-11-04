"""SQLite repository. All writes of free text pass through strip_ids (no Aadhaar / PAN / account numbers)."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from app.config import get_settings
from app.db.migrate import migrate
from app.engines.fact import Fact

Source = Literal["typed", "voice", "document"]
ItemKind = Literal["policy", "loan", "deposit", "chit", "other", "mf_holding", "stock_holding", "sip"]
Frequency = Literal["monthly", "yearly", "once"]
PROFILE_FIELDS = ("monthly_income", "monthly_expenses", "savings")  # monthly_expenses EXCLUDES loan EMIs

# ---------------------------------------------------------------- ID stripping
_AADHAAR = re.compile(r"(?<!\d)[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.I)
_LONG_DIGITS = re.compile(r"(?<![\d,.])\d{9,}(?![\d,.])")  # account / card numbers; amounts use commas
REDACTED = "[removed]"


def strip_ids(text: str | None) -> str | None:
    if text is None:
        return None
    text = _AADHAAR.sub(REDACTED, text)
    text = _PAN.sub(REDACTED, text)
    return _LONG_DIGITS.sub(REDACTED, text)


def quote_id(evidence_id: int) -> str:
    return f"q{evidence_id}"


# ---------------------------------------------------------------- models
class ProfileValue(BaseModel):
    id: int
    member_id: int
    field: str
    value: float
    unit: str
    source: Source
    source_ref: str | None
    confirmed: bool
    updated_at: str
    in_household: bool = True


class FamilyItem(BaseModel):
    id: int | None = None
    family_id: int | None = None
    kind: ItemKind
    name: str
    amount: float
    frequency: Frequency
    start_date: str | None = None
    end_date: str | None = None
    source: Source
    source_ref: str | None = None
    confirmed: bool = False
    member_id: int | None = None  # None: the family's own
    in_household: bool = True  # counts in the family budget
    units: float | None = None  # mutual fund units or number of shares
    symbol: str | None = None
    scheme: str | None = None
    category: Literal["equity", "debt", "other"] | None = None

    def monthly_amount(self) -> float:
        return {"monthly": self.amount, "yearly": self.amount / 12, "once": 0.0}[self.frequency]

    def active_on(self, day: date) -> bool:
        return (self.start_date is None or self.start_date <= day.isoformat()) and (
            self.end_date is None or self.end_date >= day.isoformat()
        )


class Quote(BaseModel):
    id: str  # "q<evidence id>"
    source: str
    text: str


class NotConfirmed(Exception):
    """Refused: only values the family confirmed may be saved."""


# ---------------------------------------------------------------- repo
class Repo:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = str(path or get_settings().db_path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        if self.path != ":memory:":
            self.conn.execute("PRAGMA journal_mode = WAL")  # readers do not block the writer
            self.conn.execute("PRAGMA busy_timeout = 5000")
        self.init_schema()

    def init_schema(self) -> None:
        migrate(self.conn)

    def ping(self) -> bool:
        return self.conn.execute("SELECT 1").fetchone()[0] == 1

    # ------------------------------------------------------------ documents (what each paper was categorised as)
    def remember_document(
        self,
        family_id: int,
        case_id: int,
        filename: str,
        sha256: str,
        doc_type: str,
        terms: dict[str, str] | None = None,
    ) -> None:
        """Saves a paper's category. A paper seen again counts up; "unknown" never replaces a real category."""
        self.conn.execute(
            """INSERT INTO document (family_id, case_id, filename, sha256, doc_type, terms_json)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT (family_id, sha256) DO UPDATE SET
                 case_id = excluded.case_id,
                 times_seen = times_seen + (excluded.case_id != document.case_id),
                 last_seen = datetime('now'),
                 doc_type = CASE WHEN excluded.doc_type = 'unknown' THEN document.doc_type ELSE excluded.doc_type END,
                 terms_json = CASE WHEN excluded.terms_json = '{}' THEN terms_json ELSE excluded.terms_json END""",
            (family_id, case_id, strip_ids(filename), sha256, doc_type, json.dumps(terms or {})),
        )
        self.conn.commit()

    def family_documents(self, family_id: int, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._rows(
            "SELECT * FROM document WHERE family_id = ? ORDER BY last_seen DESC, id DESC LIMIT ?", family_id, limit
        )
        for r in rows:
            r["terms"] = json.loads(r.pop("terms_json"))
        return rows

    def case_documents(self, case_id: int) -> list[dict[str, Any]]:
        rows = self._rows("SELECT * FROM document WHERE case_id = ? ORDER BY id", case_id)
        for r in rows:
            r["terms"] = json.loads(r.pop("terms_json"))
        return rows

    # ------------------------------------------------------------ idempotency (POST /cases)
    def idempotent_case(self, key: str, family_id: int) -> int | None:
        row = self.conn.execute(
            "SELECT case_id FROM idempotency WHERE key = ? AND family_id = ?", (key, family_id)
        ).fetchone()
        return int(row[0]) if row else None

    def claim_idempotency(self, key: str, family_id: int, case_id: int) -> bool:
        """False if another request already holds this key."""
        try:
            self.conn.execute(
                "INSERT INTO idempotency (key, family_id, case_id) VALUES (?, ?, ?)", (key, family_id, case_id)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def close(self) -> None:
        self.conn.close()

    def _insert(self, table: str, **cols: Any) -> int:
        names = ", ".join(f'"{c}"' for c in cols)
        marks = ", ".join("?" for _ in cols)
        cur = self.conn.execute(f'INSERT INTO "{table}" ({names}) VALUES ({marks})', tuple(cols.values()))
        self.conn.commit()
        return int(cur.lastrowid or 0)

    def _rows(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    # ---- family / members
    def create_family(self, language: str = "en", guardian_code: str | None = None, id: int | None = None) -> int:
        cols: dict[str, Any] = {"language": language, "guardian_code": guardian_code}
        if id is not None:
            cols["id"] = id
        return self._insert("family", **cols)

    def get_family(self, family_id: int) -> dict[str, Any] | None:
        rows = self._rows("SELECT * FROM family WHERE id = ?", family_id)
        return rows[0] if rows else None

    def add_member(self, family_id: int, name: str, role: str) -> int:
        return self._insert("member", family_id=family_id, name=strip_ids(name), role=role)

    def members(self, family_id: int) -> list[dict[str, Any]]:
        return self._rows("SELECT * FROM member WHERE family_id = ? ORDER BY id", family_id)

    def member_in_family(self, family_id: int, member_id: int) -> bool:
        return any(m["id"] == member_id for m in self.members(family_id))

    def primary_member_id(self, family_id: int) -> int | None:
        rows = self._rows("SELECT id FROM member WHERE family_id = ? AND role = 'primary' ORDER BY id", family_id)
        return rows[0]["id"] if rows else None

    # ---- profile
    def set_profile_value(
        self,
        member_id: int,
        field: str,
        value: float,
        source: Source,
        *,
        unit: str = "INR",
        source_ref: str | None = None,
        confirmed: bool,
        in_household: bool = True,
    ) -> int:
        if not confirmed:
            raise NotConfirmed(f"{field} not confirmed by the family; not saved")
        self.conn.execute(
            """INSERT INTO profile_value (member_id, field, value, unit, source, source_ref, confirmed, updated_at,
                                          in_household)
               VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now'), ?)
               ON CONFLICT (member_id, field) DO UPDATE SET value = excluded.value, unit = excluded.unit,
                 source = excluded.source, source_ref = excluded.source_ref, confirmed = 1,
                 updated_at = excluded.updated_at, in_household = excluded.in_household""",
            (member_id, field, float(value), unit, source, strip_ids(source_ref), int(in_household)),
        )
        self.conn.commit()
        return int(
            self.conn.execute(
                "SELECT id FROM profile_value WHERE member_id = ? AND field = ?", (member_id, field)
            ).fetchone()[0]
        )

    def profile_values(self, family_id: int) -> list[ProfileValue]:
        rows = self._rows(
            """SELECT pv.* FROM profile_value pv JOIN member m ON m.id = pv.member_id
               WHERE m.family_id = ? AND pv.confirmed = 1 ORDER BY pv.id""",
            family_id,
        )
        return [ProfileValue(**r) for r in rows]

    # ---- items
    def save_item(self, family_id: int, item: FamilyItem, confirmed: bool) -> int:
        if not confirmed:
            raise NotConfirmed(f"item '{item.name}' not confirmed by the family; not saved")
        data = item.model_dump(exclude={"id", "family_id", "confirmed"})
        data["name"] = strip_ids(data["name"])
        data["source_ref"] = strip_ids(data["source_ref"])
        data["scheme"] = strip_ids(data["scheme"])
        data["in_household"] = int(data["in_household"])
        return self._insert("family_item", family_id=family_id, confirmed=1, **data)

    def list_items(self, family_id: int, kind: ItemKind | None = None) -> list[FamilyItem]:
        sql, args = "SELECT * FROM family_item WHERE family_id = ? AND confirmed = 1", [family_id]
        if kind:
            sql += " AND kind = ?"
            args.append(kind)
        return [FamilyItem(**r) for r in self._rows(sql + " ORDER BY id", *args)]

    def delete_item(self, family_id: int, item_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM family_item WHERE id = ? AND family_id = ?", (item_id, family_id))
        self.conn.commit()
        return cur.rowcount > 0

    # ---- cases
    def create_case(
        self,
        family_id: int,
        *,
        case_type: str | None = None,
        transcript: str | None = None,
        language: str | None = None,
        privacy_mode: str = "discreet",
    ) -> int:
        return self._insert(
            "cases",
            family_id=family_id,
            case_type=case_type,
            transcript=strip_ids(transcript),
            language=language,
            privacy_mode=privacy_mode,
        )

    def update_case(self, case_id: int, **cols: Any) -> None:
        if "transcript" in cols:
            cols["transcript"] = strip_ids(cols["transcript"])
        sets = ", ".join(f'"{k}" = ?' for k in cols)
        self.conn.execute(f"UPDATE cases SET {sets} WHERE id = ?", (*cols.values(), case_id))
        self.conn.commit()

    def get_case(self, case_id: int) -> dict[str, Any] | None:
        rows = self._rows("SELECT * FROM cases WHERE id = ?", case_id)
        return rows[0] if rows else None

    def add_evidence(self, case_id: int, source: str, text: str) -> str:
        """Returns the quote_id ("q<id>")."""
        return quote_id(self._insert("evidence", case_id=case_id, source=source, text=strip_ids(text)))

    def get_quotes(self, case_id: int) -> list[Quote]:
        rows = self._rows("SELECT id, source, text FROM evidence WHERE case_id = ? ORDER BY id", case_id)
        return [Quote(id=quote_id(r["id"]), source=r["source"], text=r["text"]) for r in rows]

    def add_term(
        self,
        case_id: int,
        name: str,
        value: float | None,
        unit: str | None,
        *,
        evidence_id: int | None = None,
        verified: bool = False,
        reason: str | None = None,
    ) -> int:
        return self._insert(
            "term",
            case_id=case_id,
            name=name,
            value=value,
            unit=unit,
            evidence_id=evidence_id,
            verified=int(verified),
            reason=reason,
        )

    def get_terms(self, case_id: int) -> list[dict[str, Any]]:
        rows = self._rows("SELECT * FROM term WHERE case_id = ? ORDER BY id", case_id)
        for r in rows:
            r["verified"] = bool(r["verified"])
            r["quote_id"] = quote_id(r["evidence_id"]) if r["evidence_id"] else None
        return rows

    def save_facts(self, case_id: int, facts: Iterable[Fact]) -> None:
        """Upsert by (case_id, fact_id)."""
        for f in facts:
            self.conn.execute(
                """INSERT INTO fact (case_id, fact_id, label, value, unit, kind, formula, inputs_json, status,
                                     value_text)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT (case_id, fact_id) DO UPDATE SET label = excluded.label, value = excluded.value,
                     unit = excluded.unit, kind = excluded.kind, formula = excluded.formula,
                     inputs_json = excluded.inputs_json, status = excluded.status, value_text = excluded.value_text""",
                (
                    case_id,
                    f.id,
                    f.label,
                    f.value,
                    f.unit,
                    f.kind,
                    f.formula,
                    json.dumps(f.inputs, default=str),
                    f.status,
                    f.value_text,
                ),
            )
        self.conn.commit()

    def get_facts(self, case_id: int) -> list[Fact]:
        rows = self._rows("SELECT * FROM fact WHERE case_id = ? ORDER BY id", case_id)
        return [
            Fact(
                id=r["fact_id"],
                label=r["label"],
                value=r["value"],
                unit=r["unit"],
                kind=r["kind"],
                formula=r["formula"],
                inputs=json.loads(r["inputs_json"]),
                status=r["status"],
                value_text=r["value_text"],
            )
            for r in rows
        ]

    def add_position(self, case_id: int, agent: str, stance: str, strength: float, round: int = 1) -> int:
        return self._insert("position", case_id=case_id, agent=agent, round=round, stance=stance, strength=strength)

    def add_argument(
        self,
        case_id: int,
        agent: str,
        text: str,
        cited_ids: list[str],
        kept: bool,
        *,
        drop_reason: str | None = None,
        round: int = 1,
    ) -> int:
        return self._insert(
            "argument",
            case_id=case_id,
            agent=agent,
            round=round,
            text=strip_ids(text),
            cited_ids_json=json.dumps(cited_ids),
            kept=int(kept),
            drop_reason=drop_reason,
        )

    def save_verdict(
        self,
        case_id: int,
        colour: str,
        *,
        score: float | None = None,
        disagreement: float | None = None,
        overrides: list[Any] | None = None,
        sentence: str | None = None,
        questions: list[str] | None = None,
        degraded: bool = False,
    ) -> int:
        return self._insert(
            "verdict",
            case_id=case_id,
            colour=colour,
            score=score,
            disagreement=disagreement,
            overrides_json=json.dumps(overrides or [], default=lambda o: o.model_dump()),
            sentence=strip_ids(sentence),
            questions_json=json.dumps(questions or []),
            degraded=int(degraded),
        )

    def add_spoken_line(
        self,
        case_id: int,
        speaker: str,
        order: int,
        text: str,
        *,
        allowed: bool = True,
        blocked_reason: str | None = None,
    ) -> int:
        return self._insert(
            "spoken_line",
            case_id=case_id,
            speaker=speaker,
            order=order,
            text=strip_ids(text),
            allowed=int(allowed),
            blocked_reason=blocked_reason,
        )

    def create_alert(self, case_id: int, family_id: int, note: str | None = None) -> int:
        return self._insert("alert", case_id=case_id, family_id=family_id, note=strip_ids(note))

    def list_alerts(self, family_id: int, status: str | None = None) -> list[dict[str, Any]]:
        sql, args = "SELECT * FROM alert WHERE family_id = ?", [family_id]
        if status:
            sql += " AND status = ?"
            args.append(status)
        return self._rows(sql + " ORDER BY id DESC", *args)

    def update_alert(self, alert_id: int, *, status: str | None = None, note: str | None = None) -> bool:
        """note = the guardian's note for Amma (shown on her Home screen); the alert's own message is not changed."""
        cols: dict[str, Any] = {
            k: v for k, v in {"status": status, "guardian_note": strip_ids(note)}.items() if v is not None
        }
        if note is not None:
            cols["noted_at"] = datetime.now().isoformat(timespec="seconds")
        if not cols:
            return False
        sets = ", ".join(f"{k} = ?" for k in cols)
        cur = self.conn.execute(f"UPDATE alert SET {sets} WHERE id = ?", (*cols.values(), alert_id))
        self.conn.commit()
        return cur.rowcount > 0

    def add_trace(self, case_id: int, step: str, ms: float | None, outcome: str, detail: dict[str, Any] | None = None):
        return self._insert(
            "trace",
            case_id=case_id,
            step=step,
            ms=ms,
            outcome=outcome,
            detail_json=json.dumps(detail or {}, default=str),
        )

    def get_trace(self, case_id: int) -> list[dict[str, Any]]:
        rows = self._rows("SELECT * FROM trace WHERE case_id = ? ORDER BY id", case_id)
        for r in rows:
            r["detail"] = json.loads(r.pop("detail_json"))
        return rows

    def case_bundle(self, case_id: int) -> dict[str, Any] | None:
        """Everything about one case (for GET /cases/{id} and the Under the hood screen)."""
        case = self.get_case(case_id)
        if case is None:
            return None

        def j(rows: list[dict[str, Any]], *cols: str) -> list[dict[str, Any]]:
            for r in rows:
                for c in cols:
                    r[c.removesuffix("_json")] = json.loads(r.pop(c))
            return rows

        return {
            "case": case,
            "quotes": [q.model_dump() for q in self.get_quotes(case_id)],
            "terms": self.get_terms(case_id),
            "facts": [f.model_dump() for f in self.get_facts(case_id)],
            "positions": self._rows("SELECT * FROM position WHERE case_id = ? ORDER BY id", case_id),
            "arguments": j(
                self._rows("SELECT * FROM argument WHERE case_id = ? ORDER BY id", case_id), "cited_ids_json"
            ),
            "verdict": next(
                iter(
                    j(
                        self._rows("SELECT * FROM verdict WHERE case_id = ? ORDER BY id DESC LIMIT 1", case_id),
                        "overrides_json",
                        "questions_json",
                    )
                ),
                None,
            ),
            "documents": self.case_documents(case_id),
            "spoken_lines": self._rows('SELECT * FROM spoken_line WHERE case_id = ? ORDER BY "order"', case_id),
            "trace": self.get_trace(case_id),
        }
