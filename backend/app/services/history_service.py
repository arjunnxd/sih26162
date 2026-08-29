from typing import Literal

AnomalyLevel = Literal["NORMAL", "UNUSUAL", "HIGHLY_UNUSUAL"]


class HistoryThresholds:
    PROXIMITY_KM = 50.0
    MIN_HISTORICAL_COUNT = 3
    RECURRING_MIN_COUNT = 5
    ANOMALY_LOW_MAX = 30
    ANOMALY_HIGH_MAX = 70


MOCK_HISTORICAL_DATA = {
    "hotspot_001": [
        {"frp": 42.1, "detected_at": "2025-12-15T10:30:00Z"},
        {"frp": 44.8, "detected_at": "2025-11-20T10:30:00Z"},
        {"frp": 41.5, "detected_at": "2025-10-18T10:30:00Z"},
        {"frp": 43.2, "detected_at": "2025-09-22T10:30:00Z"},
        {"frp": 40.9, "detected_at": "2025-08-15T10:30:00Z"},
    ],
    "hotspot_002": [
        {"frp": 35.2, "detected_at": "2025-12-10T11:15:00Z"},
        {"frp": 37.8, "detected_at": "2025-11-12T11:15:00Z"},
    ],
    "hotspot_003": [],
}


def find_historical_data(hotspot_id: str, latitude: float, longitude: float) -> list[dict]:
    if hotspot_id in MOCK_HISTORICAL_DATA:
        return MOCK_HISTORICAL_DATA[hotspot_id]
    return []


def calculate_historical_stats(historical_records: list[dict]) -> tuple[float, float, int]:
    if not historical_records:
        return 0.0, 0.0, 0

    frp_values = [record["frp"] for record in historical_records]
    avg_frp = sum(frp_values) / len(frp_values)
    max_frp = max(frp_values)
    count = len(frp_values)

    return round(avg_frp, 2), round(max_frp, 2), count


def analyze_historical_pattern(
    hotspot_id: str,
    latitude: float,
    longitude: float,
    current_frp: float
) -> tuple[float, float, int, bool, bool, float, AnomalyLevel]:
    historical_records = find_historical_data(hotspot_id, latitude, longitude)
    historical_avg_frp, historical_max_frp, historical_detection_count = calculate_historical_stats(historical_records)

    is_recurring = historical_detection_count >= HistoryThresholds.RECURRING_MIN_COUNT
    is_new_event = historical_detection_count < HistoryThresholds.MIN_HISTORICAL_COUNT

    if historical_detection_count == 0:
        anomaly_score = 50.0
    else:
        deviation = abs(current_frp - historical_avg_frp) / max(historical_avg_frp, 1.0)
        anomaly_score = min(deviation * 100, 100.0)

    anomaly_score = round(max(0.0, min(100.0, anomaly_score)), 2)

    if anomaly_score <= HistoryThresholds.ANOMALY_LOW_MAX:
        anomaly_level: AnomalyLevel = "NORMAL"
    elif anomaly_score <= HistoryThresholds.ANOMALY_HIGH_MAX:
        anomaly_level = "UNUSUAL"
    else:
        anomaly_level = "HIGHLY_UNUSUAL"

    return (
        historical_avg_frp,
        historical_max_frp,
        historical_detection_count,
        is_recurring,
        is_new_event,
        anomaly_score,
        anomaly_level
    )