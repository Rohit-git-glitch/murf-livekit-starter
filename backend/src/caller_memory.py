"""Minimal, consent-gated persistent memory for Health Access callers."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ALLOWED_AGE_BANDS = {"child", "adolescent", "adult", "older_adult"}
ALLOWED_TRIAGE_OUTCOMES = {
    "self_care",
    "routine_consultation",
    "urgent_care",
    "emergency",
}


class CallerMemoryStore:
    """SQLite storage that intentionally contains no transcripts or medical notes."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS callers (
                    user_id TEXT PRIMARY KEY,
                    name TEXT,
                    language_preference TEXT,
                    age_band TEXT,
                    ongoing_conditions TEXT,
                    last_triage_outcome TEXT,
                    last_interaction TEXT NOT NULL
                )
                """
            )

    def lookup(self, user_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT user_id, name, language_preference, age_band,
                       ongoing_conditions, last_triage_outcome, last_interaction
                FROM callers WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return {
            "user_id": row["user_id"],
            "name": row["name"],
            "language_preference": row["language_preference"],
            "facts": {
                "age_band": row["age_band"],
                "ongoing_conditions": row["ongoing_conditions"],
                "last_triage_outcome": row["last_triage_outcome"],
            },
            "last_interaction": row["last_interaction"],
        }

    def save(
        self,
        *,
        user_id: str,
        name: str | None,
        language_preference: str | None,
        age_band: str | None,
        ongoing_conditions: str | None,
        last_triage_outcome: str | None,
    ) -> dict[str, Any]:
        self._validate_facts(age_band, ongoing_conditions, last_triage_outcome)
        timestamp = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM callers WHERE user_id = ?", (user_id,)
            ).fetchone()
            values = {
                "name": name if name is not None else self._value(existing, "name"),
                "language_preference": language_preference
                if language_preference is not None
                else self._value(existing, "language_preference"),
                "age_band": age_band
                if age_band is not None
                else self._value(existing, "age_band"),
                "ongoing_conditions": ongoing_conditions
                if ongoing_conditions is not None
                else self._value(existing, "ongoing_conditions"),
                "last_triage_outcome": last_triage_outcome
                if last_triage_outcome is not None
                else self._value(existing, "last_triage_outcome"),
            }
            connection.execute(
                """
                INSERT INTO callers (
                    user_id, name, language_preference, age_band, ongoing_conditions,
                    last_triage_outcome, last_interaction
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    name = excluded.name,
                    language_preference = excluded.language_preference,
                    age_band = excluded.age_band,
                    ongoing_conditions = excluded.ongoing_conditions,
                    last_triage_outcome = excluded.last_triage_outcome,
                    last_interaction = excluded.last_interaction
                """,
                (user_id, *values.values(), timestamp),
            )
        return self.lookup(user_id) or {}

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _value(row: sqlite3.Row | None, key: str) -> str | None:
        return row[key] if row is not None else None

    @staticmethod
    def _validate_facts(
        age_band: str | None,
        ongoing_conditions: str | None,
        last_triage_outcome: str | None,
    ) -> None:
        if age_band is not None and age_band not in ALLOWED_AGE_BANDS:
            raise ValueError("age_band must be an approved structured value")
        if (
            last_triage_outcome is not None
            and last_triage_outcome not in ALLOWED_TRIAGE_OUTCOMES
        ):
            raise ValueError("last_triage_outcome must be an approved structured value")
        if ongoing_conditions is not None and (
            len(ongoing_conditions) > 160
            or "\n" in ongoing_conditions
            or any(character in ongoing_conditions for character in ".!?")
        ):
            raise ValueError("ongoing_conditions must be a concise structured value")
