from escalation import EscalationStore
from health_access import assess_symptom_urgency
from prompt import SYSTEM_PROMPT


def test_red_flag_path_creates_an_open_request_only_after_consent(tmp_path) -> None:
    store = EscalationStore(tmp_path / "callers.sqlite3")
    store.initialize()
    triage = assess_symptom_urgency("severe chest pain")

    denied = store.create(
        caller_id="caller-om",
        caller_name="Om",
        reason="red_flag_symptom",
        current_issue="severe chest pain",
        what_was_checked=f"Symptom urgency assessment: {triage['triage_level']}",
        urgency="high",
        language="English",
        preferred_follow_up="phone",
        consent_given=False,
    )
    assert denied == {
        "success": False,
        "status": "not_created",
        "reason": "consent_required",
    }
    assert store.list_open() == []

    created = store.create(
        caller_id="caller-om",
        caller_name="Om",
        reason="red_flag_symptom",
        current_issue="severe chest pain",
        what_was_checked=(
            "Symptom urgency assessment: emergency; caller also requested diagnosis"
        ),
        urgency="high",
        language="English",
        preferred_follow_up="phone",
        consent_given=True,
    )

    assert created["success"] is True
    assert created["status"] == "open"
    assert created["escalation_id"].startswith("ESC-")
    request = store.list_open()[0]
    assert request["escalation_id"] == created["escalation_id"]
    assert request["reason"] == "red_flag_symptom"
    assert "severe chest pain" in request["summary"]


def test_red_flag_prompt_requires_offer_then_separate_sharing_consent() -> None:
    emergency_guidance = "call local emergency services or go to the nearest"
    human_help_offer = (
        "I can also create a human-help request for a health-support representative."
    )
    sharing_permission = "Ask for explicit permission to share that information."
    normalized_prompt = " ".join(SYSTEM_PROMPT.split())

    assert emergency_guidance in normalized_prompt
    assert human_help_offer in normalized_prompt
    assert sharing_permission in normalized_prompt
    assert normalized_prompt.index(emergency_guidance) < normalized_prompt.index(
        human_help_offer
    )
    assert normalized_prompt.index(human_help_offer) < normalized_prompt.index(
        sharing_permission
    )
    assert "do not create a request yet" in normalized_prompt
    assert "must not delay emergency care" in normalized_prompt


def test_normal_self_care_path_does_not_create_an_escalation(tmp_path) -> None:
    store = EscalationStore(tmp_path / "callers.sqlite3")
    store.initialize()

    triage = assess_symptom_urgency("mild headache since this morning")

    assert triage["triage_level"] == "self_care"
    # Normal self-care guidance does not invoke EscalationStore.create at all.
    assert store.list_open() == []


def test_escalation_rejects_sensitive_or_unnecessary_data(tmp_path) -> None:
    store = EscalationStore(tmp_path / "callers.sqlite3")
    store.initialize()

    result = store.create(
        caller_id="caller-1",
        caller_name="Om",
        reason="diagnosis_request",
        current_issue="Please diagnose my headache; my OTP is 123456",
        what_was_checked="Caller requested a diagnosis",
        urgency="normal",
        language="English",
        preferred_follow_up=None,
        consent_given=True,
    )

    assert result == {
        "success": False,
        "status": "not_created",
        "reason": "invalid_request",
    }
    assert store.list_open() == []
