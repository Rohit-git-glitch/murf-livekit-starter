"""Deterministic triage and live public-facility lookup helpers.

Facility listings come from OpenStreetMap's Nominatim and Overpass public APIs.
They are map listings, not a confirmation that a facility is open or provides a
particular service.
"""

import json
import math
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

REQUEST_TIMEOUT_SECONDS = 6
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
]
USER_AGENT = "AarogyaAI-HealthAccess/1.0 (educational project)"


def _india_timestamp() -> str:
    india_timezone = timezone(timedelta(hours=5, minutes=30), name="IST")
    return datetime.now(UTC).astimezone(india_timezone).isoformat()


def _request_json(url: str, params: dict[str, str], timeout: int = REQUEST_TIMEOUT_SECONDS) -> Any:
    request = Request(
        f"{url}?{urlencode(params)}",
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _distance_km(
    first_latitude: float,
    first_longitude: float,
    second_latitude: float,
    second_longitude: float,
) -> float:
    radius_km = 6371.0
    latitude_delta = math.radians(second_latitude - first_latitude)
    longitude_delta = math.radians(second_longitude - first_longitude)
    a = (
        math.sin(latitude_delta / 2) ** 2
        + math.cos(math.radians(first_latitude))
        * math.cos(math.radians(second_latitude))
        * math.sin(longitude_delta / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def assess_symptom_urgency(
    symptoms: str,
    duration: str | None = None,
    age_band: str | None = None,
    pregnancy_or_high_risk: bool = False,
) -> dict[str, Any]:
    """Return a conservative, non-diagnostic triage level from caller-reported data."""
    normalized = symptoms.lower().strip()
    assessed_at = _india_timestamp()
    if not normalized:
        return {
            "status": "needs_more_information",
            "message": "Please describe the symptoms before an urgency level is assessed.",
            "assessed_at": assessed_at,
        }

    emergency_signs = (
        "chest pain",
        "trouble breathing",
        "difficulty breathing",
        "cannot breathe",
        "severe bleeding",
        "unconscious",
        "passed out",
        "seizure",
        "stroke",
        "face drooping",
        "slurred speech",
        "poison",
        "suicidal",
        "self harm",
        "severe allergic",
        "swelling of lips",
    )
    urgent_signs = (
        "high fever",
        "persistent vomiting",
        "vomiting blood",
        "blood in stool",
        "severe pain",
        "severe headache",
        "confusion",
        "dehydrated",
        "not urinating",
        "fainting",
    )
    if any(sign in normalized for sign in emergency_signs):
        return _triage_result(
            "emergency",
            "A reported warning sign may need emergency assessment now.",
            assessed_at,
            "Call local emergency services or go to the nearest emergency department now.",
        )
    if any(sign in normalized for sign in urgent_signs):
        return _triage_result(
            "urgent_care",
            "A reported symptom may need same-day clinical assessment.",
            assessed_at,
            "Seek urgent medical care today. If symptoms worsen, use emergency services.",
        )
    if pregnancy_or_high_risk or age_band in {"child", "older_adult"}:
        return _triage_result(
            "routine_consultation",
            "Higher-risk callers should discuss new symptoms with a clinician sooner.",
            assessed_at,
            "Arrange a clinician or PHC consultation, especially if symptoms persist or worsen.",
        )
    if duration and any(
        term in duration.lower() for term in ("week", "several day", "more than 3")
    ):
        return _triage_result(
            "routine_consultation",
            "Symptoms lasting several days should be assessed by a clinician.",
            assessed_at,
            "Arrange a routine consultation or visit a PHC.",
        )
    return _triage_result(
        "self_care",
        "No listed emergency warning sign was reported in the information provided.",
        assessed_at,
        "Rest, fluids, and monitoring may be reasonable; seek care if symptoms worsen or warning signs appear.",
    )


def _triage_result(
    level: str, reason: str, assessed_at: str, next_step: str
) -> dict[str, str]:
    return {
        "status": "ok",
        "triage_level": level,
        "reason": reason,
        "next_step": next_step,
        "assessment_note": "This is general guidance, not a diagnosis.",
        "assessed_at": assessed_at,
    }


def find_nearby_health_facilities(location: str, limit: int = 3) -> dict[str, Any]:
    """Look up nearby health facilities using live OpenStreetMap public data."""
    checked_at = _india_timestamp()
    if not location.strip():
        return {
            "status": "needs_location",
            "message": "Please provide a PIN code, locality, town, or nearby landmark.",
            "data_checked_at": checked_at,
        }
    try:
        geocoded = _request_json(
            NOMINATIM_URL,
            {"q": f"{location}, India", "format": "jsonv2", "limit": "1"},
        )
        if not geocoded:
            return {
                "status": "not_found",
                "message": "The location could not be found. Ask for a PIN code or a more specific locality.",
                "data_checked_at": checked_at,
            }
        latitude = float(geocoded[0]["lat"])
        longitude = float(geocoded[0]["lon"])
        searched_location = geocoded[0].get("display_name", location)

        overpass_query = (
            "[out:json][timeout:5];("
            f'nwr(around:5000,{latitude},{longitude})[amenity~"hospital|clinic|doctors"];'
            ");out center tags 30;"
        )
        payload = None
        for endpoint in OVERPASS_ENDPOINTS:
            try:
                payload = _request_json(endpoint, {"data": overpass_query})
                if payload and isinstance(payload, dict) and "elements" in payload and payload["elements"]:
                    break
            except Exception:
                continue

        facilities = []
        if payload and isinstance(payload, dict) and payload.get("elements"):
            for element in payload.get("elements", []):
                tags = element.get("tags", {})
                facility_latitude = element.get("lat", element.get("center", {}).get("lat"))
                facility_longitude = element.get("lon", element.get("center", {}).get("lon"))
                if facility_latitude is None or facility_longitude is None:
                    continue
                facility_type = (
                    tags.get("healthcare") or tags.get("amenity") or "health facility"
                )
                address = ", ".join(
                    value
                    for value in (
                        tags.get("addr:street"),
                        tags.get("addr:suburb"),
                        tags.get("addr:city"),
                    )
                    if value
                )
                facilities.append(
                    {
                        "name": tags.get("name", "Health Facility / Clinic"),
                        "type": facility_type.replace("_", " "),
                        "address": address or None,
                        "distance_km": round(
                            _distance_km(
                                latitude,
                                longitude,
                                float(facility_latitude),
                                float(facility_longitude),
                            ),
                            1,
                        ),
                        "latitude": facility_latitude,
                        "longitude": facility_longitude,
                    }
                )

        # High-availability Fallback: Direct Nominatim Healthcare search if Overpass is empty or down
        if not facilities:
            try:
                direct_health = _request_json(
                    NOMINATIM_URL,
                    {"q": f"hospital, {location}, India", "format": "jsonv2", "limit": "5"},
                )
                if isinstance(direct_health, list):
                    for item in direct_health:
                        fac_lat = float(item["lat"])
                        fac_lon = float(item["lon"])
                        raw_name = item.get("name") or item.get("display_name", "").split(",")[0]
                        facilities.append(
                            {
                                "name": raw_name if raw_name else "Local Health Facility",
                                "type": item.get("type", "hospital").replace("_", " "),
                                "address": item.get("display_name"),
                                "distance_km": round(
                                    _distance_km(latitude, longitude, fac_lat, fac_lon), 1
                                ),
                                "latitude": fac_lat,
                                "longitude": fac_lon,
                            }
                        )
            except Exception:
                pass

    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        return {
            "status": "unavailable",
            "message": "Live map data could not be reached right now.",
            "data_checked_at": checked_at,
        }

    facilities.sort(key=lambda facility: facility["distance_km"])
    if not facilities:
        return {
            "status": "not_found",
            "message": "No mapped health facility was found near this location.",
            "searched_location": searched_location,
            "source": "OpenStreetMap (Nominatim and Overpass)",
            "data_checked_at": checked_at,
        }
    return {
        "status": "ok",
        "searched_location": searched_location,
        "facilities": facilities[: max(1, min(limit, 5))],
        "source": "OpenStreetMap (Nominatim and Overpass)",
        "data_checked_at": checked_at,
        "data_note": "Listings do not confirm hours, availability, or services. Call the facility before travelling.",
    }
