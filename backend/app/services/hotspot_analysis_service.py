"""Centralized hotspot analysis pipeline for the SIH26162 intelligence layer.

Pipeline order (matches the platform architecture):

    RAW HOTSPOT
        ↓
    RISK ANALYSIS            risk_service.classify_risk(frp, confidence)
        ↓
    HISTORICAL ANALYSIS      history_service.analyze_historical_pattern(...)
        ↓
    ANOMALY ANALYSIS         (returned alongside the historical pattern)
        ↓
    GEOSPATIAL ANALYSIS      proximity_service.analyze_infrastructure_proximity(lat, lon)
        ↓
    PRIORITY ANALYSIS        priority_service.analyze_priority(...) with geospatial signals
        ↓
    EVENT CLASSIFICATION     classification_service.classify_thermal_event_from_signals(...)
        ↓
    FINAL ANALYZED HOTSPOT

Geospatial / proximity intelligence is OPTIONAL:
  * The industrial-proximity score and the near-critical-infrastructure flag are
    fed into the priority analysis (the priority service already supports them).
  * Every proximity signal is also forwarded to the event classifier.
  * When infrastructure data is unavailable (missing file/empty dataset) or the
    coordinates are invalid, the proximity service reports a structured ``error``
    and all geospatial fields are set to ``None``, so priority and classification
    degrade safely without fabricated scores.
"""

from typing import Optional

from app.services.risk_service import classify_risk
from app.services.history_service import analyze_historical_pattern
from app.services.priority_service import analyze_priority
from app.services.proximity_service import analyze_infrastructure_proximity
from app.services.classification_service import classify_thermal_event_from_signals


def analyze_hotspot(raw_hotspot: dict) -> dict:
    """Centralized analysis pipeline for a single hotspot.

    Runs the complete analysis pipeline:
    1. Risk Analysis
    2. Historical Analysis (includes anomaly analysis)
    3. Geospatial / Proximity Analysis
    4. Priority Analysis (fed by risk, anomaly, and geospatial signals)
    5. Event Classification (explainable decision-support label)

    Returns the complete analyzed hotspot dictionary.
    """
    hotspot = raw_hotspot.copy()

    # ------------------------------------------------------------------
    # 1. Risk Analysis
    # ------------------------------------------------------------------
    risk_level, risk_score = classify_risk(hotspot["frp"], hotspot["confidence"])
    hotspot["risk_level"] = risk_level
    hotspot["risk_score"] = risk_score

    # ------------------------------------------------------------------
    # 2. Historical Analysis (historical stats + anomaly analysis)
    # ------------------------------------------------------------------
    (historical_avg_frp, historical_max_frp, historical_detection_count,
     is_recurring, is_new_event, anomaly_score, anomaly_level) = analyze_historical_pattern(
        hotspot["id"], hotspot["latitude"], hotspot["longitude"], hotspot["frp"]
    )
    hotspot["historical_avg_frp"] = historical_avg_frp
    hotspot["historical_max_frp"] = historical_max_frp
    hotspot["historical_detection_count"] = historical_detection_count
    hotspot["is_recurring"] = is_recurring
    hotspot["is_new_event"] = is_new_event
    hotspot["anomaly_score"] = anomaly_score
    hotspot["anomaly_level"] = anomaly_level

    # ------------------------------------------------------------------
    # 3. Geospatial / Proximity Analysis
    #
    #    ``analyze_infrastructure_proximity`` never raises for data problems:
    #      - invalid coordinates   -> error = "invalid_coordinates"
    #      - missing/empty dataset -> error = "no_facilities_available"
    #    When an error is reported, all geospatial fields are set to None so
    #    downstream stages see genuinely absent optional signals.
    # ------------------------------------------------------------------
    proximity = analyze_infrastructure_proximity(
        hotspot.get("latitude"), hotspot.get("longitude")
    )
    if proximity.get("error") is None:
        hotspot["nearest_facility_name"] = proximity["nearest_facility_name"]
        hotspot["nearest_facility_type"] = proximity["nearest_facility_type"]
        hotspot["nearest_facility_distance_m"] = proximity["nearest_facility_distance_m"]
        hotspot["nearby_facility_count"] = proximity["nearby_facility_count"]
        hotspot["industrial_proximity_score"] = proximity["industrial_proximity_score"]
        hotspot["near_critical_infrastructure"] = proximity["near_critical_infrastructure"]
    else:
        hotspot["nearest_facility_name"] = None
        hotspot["nearest_facility_type"] = None
        hotspot["nearest_facility_distance_m"] = None
        hotspot["nearby_facility_count"] = None
        hotspot["industrial_proximity_score"] = None
        hotspot["near_critical_infrastructure"] = None

    # ------------------------------------------------------------------
    # 4. Priority Analysis (already accepts optional geospatial signals)
    # ------------------------------------------------------------------
    priority_score, priority_level, priority_factors = analyze_priority(
        risk_score=risk_score,
        anomaly_score=anomaly_score,
        is_new_event=is_new_event,
        is_recurring=is_recurring,
        industrial_proximity_score=hotspot["industrial_proximity_score"],
        near_critical_infrastructure=hotspot["near_critical_infrastructure"],
    )
    hotspot["priority_score"] = priority_score
    hotspot["priority_level"] = priority_level
    hotspot["priority_factors"] = priority_factors

    # ------------------------------------------------------------------
    # 5. Event Classification
    #
    #    ``classify_thermal_event_from_signals`` safely filters arbitrary dicts
    #    to its known signal fields, so passing the full analyzed hotspot is OK.
    # ------------------------------------------------------------------
    classification = classify_thermal_event_from_signals(hotspot)
    hotspot["event_type"] = classification["event_type"]
    hotspot["classification_confidence"] = classification["classification_confidence"]
    hotspot["classification_reasons"] = classification["classification_reasons"]
    hotspot["matched_signals"] = classification["matched_signals"]
    hotspot["classification_score_breakdown"] = classification["classification_score_breakdown"]
    hotspot["disclaimer"] = classification["disclaimer"]

    return hotspot


def get_mock_hotspots() -> list[dict]:
    """Return the mock hotspot data."""
    return [
        {
            "id": "hotspot_001",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "detected_at": "2026-01-15T10:30:00Z",
            "brightness": 320.5,
            "frp": 45.2,
            "confidence": 0.92
        },
        {
            "id": "hotspot_002",
            "latitude": 19.0760,
            "longitude": 72.8777,
            "detected_at": "2026-01-15T11:15:00Z",
            "brightness": 310.8,
            "frp": 38.7,
            "confidence": 0.88
        },
        {
            "id": "hotspot_003",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "detected_at": "2026-01-15T12:00:00Z",
            "brightness": 330.1,
            "frp": 52.4,
            "confidence": 0.95
        }
    ]


def find_raw_hotspot(hotspot_id: str) -> Optional[dict]:
    """Find a raw hotspot by ID from mock data."""
    for hotspot in get_mock_hotspots():
        if hotspot["id"] == hotspot_id:
            return hotspot
    return None