import pytest

from call_analytics import CallAnalyticsStore, CallOutcomeTracker


def test_completed_call_analytics_are_calculated_from_sqlite(tmp_path) -> None:
    store = CallAnalyticsStore(tmp_path / "callers.sqlite3")
    store.initialize()
    store.record_call_outcome("room-success", "successful")
    store.record_call_outcome("room-failure", "failed")

    assert store.get_call_analytics() == {
        "total_calls": 2,
        "successful_calls": 1,
        "failed_calls": 1,
    }


def test_recording_the_same_call_twice_does_not_double_count(tmp_path) -> None:
    store = CallAnalyticsStore(tmp_path / "callers.sqlite3")
    store.initialize()
    store.record_call_outcome("room-1", "successful")
    store.record_call_outcome("room-1", "failed")

    assert store.get_call_analytics() == {
        "total_calls": 1,
        "successful_calls": 1,
        "failed_calls": 0,
    }


def test_call_is_successful_only_after_guidance_or_escalation() -> None:
    incomplete_call = CallOutcomeTracker()
    guidance_call = CallOutcomeTracker()
    escalation_call = CallOutcomeTracker()

    guidance_call.mark_safe_guidance_provided()
    escalation_call.mark_escalation_communicated()

    assert incomplete_call.outcome == "failed"
    assert guidance_call.outcome == "successful"
    assert escalation_call.outcome == "successful"


def test_invalid_outcomes_are_rejected(tmp_path) -> None:
    store = CallAnalyticsStore(tmp_path / "callers.sqlite3")
    store.initialize()

    with pytest.raises(ValueError, match="successful or failed"):
        store.record_call_outcome("room-1", "connected")
