"""Minimal, consent-gated SQLite storage for human-help requests.

Only a concise escalation summary is stored. This module intentionally never
stores conversation transcripts or detailed medical notes.
"""

from __future__ import annotations

import logging
import re
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ALLOWED_REASONS = {"red_flag_symptom", "diagnosis_request"}
ALLOWED_URGENCY = {"high", "urgent", "normal"}
SENSITIVE_VALUE_PATTERN = re.compile(
    r"\b(?:password|passcode|otp|one[ -]?time[ -]?password|pin|"
    r"bank(?:\s+account)?(?:\s+number)?|account\s+number)\b",
    re.IGNORECASE,
)
INDIA_TIMEZONE = timezone(timedelta(hours=5, minutes=30), name="IST")
MAX_FIELD_LENGTHS = {
    "caller_id": 128,
    "caller_name": 120,
    "reason": 32,
    "current_issue": 240,
    "what_was_checked": 240,
    "urgency": 16,
    "language": 40,
    "preferred_follow_up": 80,
}


class EscalationStore:
    """Create and inspect concise, privacy-filtered human-help requests."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS escalation_requests (
                    escalation_id TEXT PRIMARY KEY,
                    caller_id TEXT NOT NULL,
                    caller_name TEXT,
                    reason TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    what_was_checked TEXT NOT NULL,
                    urgency TEXT NOT NULL,
                    language TEXT NOT NULL,
                    preferred_follow_up TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_escalation_requests_open
                ON escalation_requests (status, created_at DESC)
                """
            )

    def create(
        self,
        *,
        caller_id: str,
        caller_name: str | None,
        reason: str,
        current_issue: str,
        what_was_checked: str,
        urgency: str,
        language: str,
        preferred_follow_up: str | None,
        consent_given: bool,
    ) -> dict[str, str | bool]:
        """Persist the smallest useful escalation record after clear consent."""
        if not consent_given:
            return {
                "success": False,
                "status": "not_created",
                "reason": "consent_required",
            }
        try:
            self._validate_fields(
                caller_id=caller_id,
                caller_name=caller_name,
                reason=reason,
                current_issue=current_issue,
                what_was_checked=what_was_checked,
                urgency=urgency,
                language=language,
                preferred_follow_up=preferred_follow_up,
            )
        except ValueError as error:
            logger.warning("Escalation request rejected: %s", error)
            return {
                "success": False,
                "status": "not_created",
                "reason": "invalid_request",
            }

        created_at = datetime.now(UTC).astimezone(INDIA_TIMEZONE).isoformat()
        summary = self._build_summary(
            caller_name or caller_id,
            current_issue,
            what_was_checked,
            urgency,
            language,
            preferred_follow_up,
        )
        for _ in range(3):
            escalation_id = self._new_id()
            try:
                with self._connect() as connection:
                    connection.execute(
                        """
                        INSERT INTO escalation_requests (
                            escalation_id, caller_id, caller_name, reason, summary,
                            what_was_checked, urgency, language, preferred_follow_up,
                            status, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
                        """,
                        (
                            escalation_id,
                            caller_id,
                            caller_name,
                            reason,
                            summary,
                            what_was_checked,
                            urgency,
                            language,
                            preferred_follow_up,
                            created_at,
                        ),
                    )
                logger.info("Human-help request created: %s", escalation_id)
                return {
                    "success": True,
                    "status": "open",
                    "escalation_id": escalation_id,
                }
            except sqlite3.IntegrityError:
                continue
            except sqlite3.Error:
                logger.exception("Human-help request storage failed")
                return {
                    "success": False,
                    "status": "not_created",
                    "reason": "storage_failed",
                }
        logger.error("Could not allocate a unique human-help request ID")
        return {
            "success": False,
            "status": "not_created",
            "reason": "id_generation_failed",
        }

    def list_open(self) -> list[dict[str, Any]]:
        """Return open requests for an authorised local support workflow."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT escalation_id, caller_id, caller_name, reason, summary,
                       what_was_checked, urgency, language, preferred_follow_up,
                       status, created_at
                FROM escalation_requests
                WHERE status = 'open'
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _new_id() -> str:
        date = datetime.now(UTC).astimezone(INDIA_TIMEZONE).strftime("%Y%m%d")
        return f"ESC-{date}-{secrets.token_hex(2).upper()}"

    @staticmethod
    def _build_summary(
        caller: str,
        issue: str,
        checked: str,
        urgency: str,
        language: str,
        follow_up: str | None,
    ) -> str:
        follow_up_text = follow_up or "not provided"
        return (
            f"Caller: {caller}. Issue: {issue}. Checked: {checked}. "
            f"Urgency: {urgency}. Language: {language}. Follow-up: {follow_up_text}."
        )

    @staticmethod
    def _validate_fields(**fields: str | None) -> None:
        caller_id = fields["caller_id"]
        reason = fields["reason"]
        urgency = fields["urgency"]
        required_fields = {
            "caller_id",
            "reason",
            "current_issue",
            "what_was_checked",
            "urgency",
            "language",
        }
        if (
            not isinstance(caller_id, str)
            or not caller_id
            or len(caller_id) > MAX_FIELD_LENGTHS["caller_id"]
        ):
            raise ValueError("invalid caller ID")
        if reason not in ALLOWED_REASONS:
            raise ValueError("unsupported escalation reason")
        if urgency not in ALLOWED_URGENCY:
            raise ValueError("unsupported urgency")
        for field_name, value in fields.items():
            if value is None:
                if field_name in required_fields:
                    raise ValueError(f"missing {field_name}")
                continue
            if not isinstance(value, str):
                raise ValueError(f"invalid {field_name}")
            if len(value.strip()) == 0 or len(value) > MAX_FIELD_LENGTHS[field_name]:
                raise ValueError(f"invalid {field_name}")
            if "\n" in value:
                raise ValueError(f"multiline {field_name}")
            if SENSITIVE_VALUE_PATTERN.search(value):
                raise ValueError(f"sensitive information in {field_name}")
