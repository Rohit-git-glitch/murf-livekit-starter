"""Privacy-preserving SQLite storage for completed call outcomes."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

CALL_OUTCOMES = {"successful", "failed"}


class CallOutcomeTracker:
    """Tracks whether a live session reached a Health Access success state."""

    def __init__(self) -> None:
        self._safe_guidance_provided = False
        self._escalation_communicated = False

    def mark_safe_guidance_provided(self) -> None:
        self._safe_guidance_provided = True

    def mark_escalation_communicated(self) -> None:
        self._escalation_communicated = True

    @property
    def outcome(self) -> str:
        if self._safe_guidance_provided or self._escalation_communicated:
            return "successful"
        return "failed"


class CallAnalyticsStore:
    """Stores only a call ID, final outcome, and completion timestamp."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS call_outcomes (
                    call_id TEXT PRIMARY KEY,
                    outcome TEXT NOT NULL CHECK (outcome IN ('successful', 'failed')),
                    created_at TEXT NOT NULL
                )
                """
            )

    def record_call_outcome(self, call_id: str, outcome: str) -> None:
        if not call_id:
            raise ValueError("call_id is required")
        if outcome not in CALL_OUTCOMES:
            raise ValueError("outcome must be successful or failed")

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO call_outcomes (call_id, outcome, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(call_id) DO NOTHING
                """,
                (call_id, outcome, datetime.now(UTC).isoformat()),
            )

    def get_call_analytics(self) -> dict[str, int]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_calls,
                    SUM(CASE WHEN outcome = 'successful' THEN 1 ELSE 0 END)
                        AS successful_calls,
                    SUM(CASE WHEN outcome = 'failed' THEN 1 ELSE 0 END)
                        AS failed_calls
                FROM call_outcomes
                """
            ).fetchone()
        return {
            "total_calls": int(row["total_calls"] or 0),
            "successful_calls": int(row["successful_calls"] or 0),
            "failed_calls": int(row["failed_calls"] or 0),
        }

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection
