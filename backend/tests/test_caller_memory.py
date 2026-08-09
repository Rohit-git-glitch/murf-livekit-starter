import pytest

from caller_memory import CallerMemoryStore


def test_memory_round_trip_contains_only_structured_fields(tmp_path) -> None:
    store = CallerMemoryStore(tmp_path / "callers.sqlite3")
    store.initialize()
    saved = store.save(
        user_id="caller-1",
        name="Ramesh",
        language_preference="Hindi",
        age_band="adult",
        ongoing_conditions="diabetes, hypertension",
        last_triage_outcome="routine_consultation",
    )
    assert saved == store.lookup("caller-1")
    assert saved["facts"]["last_triage_outcome"] == "routine_consultation"


def test_memory_updates_without_overwriting_unspecified_facts(tmp_path) -> None:
    store = CallerMemoryStore(tmp_path / "callers.sqlite3")
    store.initialize()
    store.save(
        user_id="caller-1",
        name="Ramesh",
        language_preference="Hindi",
        age_band="adult",
        ongoing_conditions="diabetes",
        last_triage_outcome="self_care",
    )
    saved = store.save(
        user_id="caller-1",
        name=None,
        language_preference=None,
        age_band=None,
        ongoing_conditions=None,
        last_triage_outcome="routine_consultation",
    )
    assert saved["name"] == "Ramesh"
    assert saved["facts"]["ongoing_conditions"] == "diabetes"
    assert saved["facts"]["last_triage_outcome"] == "routine_consultation"


def test_memory_rejects_note_like_condition_text(tmp_path) -> None:
    store = CallerMemoryStore(tmp_path / "callers.sqlite3")
    store.initialize()

    with pytest.raises(ValueError, match="concise structured"):
        store.save(
            user_id="caller-1",
            name=None,
            language_preference=None,
            age_band=None,
            ongoing_conditions="Caller said they have had pain for weeks.",
            last_triage_outcome=None,
        )
