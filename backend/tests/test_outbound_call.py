import json
import pytest
from agent import Assistant
from outbound_call import HEALTH_ACCESS_TRIGGERS, sip_trunk_id


def test_sip_trunk_id_configuration():
    assert sip_trunk_id == "ST_FFxPtX5eQVzN"


def test_health_access_triggers_defined():
    assert "medication_reminder" in HEALTH_ACCESS_TRIGGERS
    assert "vaccination_reminder" in HEALTH_ACCESS_TRIGGERS
    assert "triage_followup" in HEALTH_ACCESS_TRIGGERS


def test_assistant_initialization_with_caller_info():
    caller_info = {
        "caller_user_id": "test_user_001",
        "lookercaller": {"name": "Aarav", "ongoing_conditions": "Hypertension"},
        "call_trigger": "Medication Reminder",
        "instructions": "Remind patient to take amlodipine on time.",
    }

    assistant = Assistant(
        caller_user_id="test_user_001",
        caller_info=caller_info,
    )

    instructions_text = assistant.instructions
    assert "test_user_001" in instructions_text
    assert "Medication Reminder" in instructions_text
    assert "Aarav" in instructions_text
    assert "Remind patient to take amlodipine on time." in instructions_text
