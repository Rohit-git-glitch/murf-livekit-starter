from urllib.error import URLError

import health_access


def test_triage_escalates_chest_pain() -> None:
    result = health_access.assess_symptom_urgency(
        "I have chest pain and cannot breathe"
    )

    assert result["triage_level"] == "emergency"
    assert result["assessed_at"].endswith("+05:30")


def test_triage_uses_self_care_when_no_warning_sign_is_reported() -> None:
    result = health_access.assess_symptom_urgency("Mild cough since this morning")

    assert result["triage_level"] == "self_care"
    assert result["assessment_note"] == "This is general guidance, not a diagnosis."


def test_facility_lookup_returns_live_data_shape(monkeypatch) -> None:
    responses = [
        [{"lat": "19.0760", "lon": "72.8777", "display_name": "Mumbai, India"}],
        {
            "elements": [
                {
                    "lat": 19.08,
                    "lon": 72.88,
                    "tags": {"name": "Example PHC", "healthcare": "primary_care"},
                }
            ]
        },
    ]

    def fake_request_json(url: str, params: dict[str, str]):
        return responses.pop(0)

    monkeypatch.setattr(health_access, "_request_json", fake_request_json)
    result = health_access.find_nearby_health_facilities("Mumbai")

    assert result["status"] == "ok"
    assert result["facilities"][0]["name"] == "Example PHC"
    assert result["data_checked_at"].endswith("+05:30")


def test_facility_lookup_has_a_safe_network_failure(monkeypatch) -> None:
    def failing_request_json(url: str, params: dict[str, str]):
        raise URLError("offline")

    monkeypatch.setattr(health_access, "_request_json", failing_request_json)
    result = health_access.find_nearby_health_facilities("Pune")

    assert result["status"] == "unavailable"
    assert "could not be reached" in result["message"]
