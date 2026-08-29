from typing import Optional
from app.services.risk_service import classify_risk
from app.services.history_service import analyze_historical_pattern
from app.services.priority_service import analyze_priority


def analyze_hotspot(raw_hotspot: dict) -> dict:
    """Centralized analysis pipeline for a single hotspot.
    
    Runs the complete analysis pipeline:
    1. Risk Analysis
    2. Historical Analysis
    3. Priority Analysis (includes anomaly)
    
    Returns the complete analyzed hotspot dictionary.
    """
    hotspot = raw_hotspot.copy()
    
    # Risk Analysis
    risk_level, risk_score = classify_risk(hotspot["frp"], hotspot["confidence"])
    hotspot["risk_level"] = risk_level
    hotspot["risk_score"] = risk_score

    # Historical Analysis
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

    # Priority Analysis
    priority_score, priority_level, priority_factors = analyze_priority(
        risk_score=risk_score,
        anomaly_score=anomaly_score,
        is_new_event=is_new_event,
        is_recurring=is_recurring,
    )
    hotspot["priority_score"] = priority_score
    hotspot["priority_level"] = priority_level
    hotspot["priority_factors"] = priority_factors

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