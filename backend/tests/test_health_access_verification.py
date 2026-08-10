import pytest
from caller_memory import CallerMemoryStore
from health_access import assess_symptom_urgency, find_nearby_health_facilities

def test_triage_urgency_categories():
    # Emergency category
    resp_emerg = assess_symptom_urgency("I have severe chest pain and trouble breathing")
    assert resp_emerg["status"] == "ok"
    assert resp_emerg["triage_level"] == "emergency"
    assert "emergency" in resp_emerg["next_step"].lower()

    # Urgent care category
    resp_urgent = assess_symptom_urgency("High fever and persistent vomiting")
    assert resp_urgent["status"] == "ok"
    assert resp_urgent["triage_level"] == "urgent_care"

    # Routine consultation category (older adult or prolonged duration)
    resp_routine = assess_symptom_urgency("Coughing for several days", age_band="older_adult")
    assert resp_routine["status"] == "ok"
    assert resp_routine["triage_level"] == "routine_consultation"

    # Self-care category
    resp_self = assess_symptom_urgency("Mild nasal congestion since this morning")
    assert resp_self["status"] == "ok"
    assert resp_self["triage_level"] == "self_care"
    assert resp_self["assessment_note"] == "This is general guidance, not a diagnosis."

def test_facility_lookup_data_handling(monkeypatch):
    # Mocking successful OSM Nominatim + Overpass lookup
    def fake_request_json(url, params):
        if "nominatim" in url:
            return [{"lat": "28.6139", "lon": "77.2090", "display_name": "New Delhi, Delhi, India"}]
        else:
            return {
                "elements": [
                    {
                        "lat": 28.6150,
                        "lon": 77.2100,
                        "tags": {
                            "name": "City Clinic",
                            "amenity": "clinic",
                            "addr:street": "MG Road"
                        }
                    }
                ]
            }

    monkeypatch.setattr("health_access._request_json", fake_request_json)
    result = find_nearby_health_facilities("Connaught Place, New Delhi")

    assert result["status"] == "ok"
    assert "data_checked_at" in result
    assert result["data_checked_at"].endswith("+05:30")
    assert len(result["facilities"]) == 1
    assert result["facilities"][0]["name"] == "City Clinic"
    assert result["data_note"] == "Listings do not confirm hours, availability, or services. Call the facility before travelling."

def test_facility_lookup_network_error(monkeypatch):
    def failing_request(url, params):
        from urllib.error import URLError
        raise URLError("Network unreachable")

    monkeypatch.setattr("health_access._request_json", failing_request)
    result = find_nearby_health_facilities("400001")

    assert result["status"] == "unavailable"
    assert "message" in result
    assert "data_checked_at" in result
