from pydantic import BaseModel
from typing import Any, Dict, List, Literal, Optional


RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
AnomalyLevel = Literal["NORMAL", "UNUSUAL", "HIGHLY_UNUSUAL"]
PriorityLevel = Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
EventType = Literal[
    "NORMAL_RECURRING_ACTIVITY",
    "INDUSTRIAL_THERMAL_ACTIVITY",
    "UNUSUAL_THERMAL_EVENT",
    "HIGH_PRIORITY_INCIDENT",
    "UNKNOWN",
]


class Hotspot(BaseModel):
    id: str
    latitude: float
    longitude: float
    detected_at: str
    brightness: float
    frp: float
    confidence: float
    risk_level: RiskLevel
    risk_score: float
    historical_avg_frp: float
    historical_max_frp: float
    historical_detection_count: int
    is_recurring: bool
    is_new_event: bool
    anomaly_score: float
    anomaly_level: AnomalyLevel
    priority_score: float
    priority_level: PriorityLevel
    priority_factors: List[str]

    # --- Geospatial / proximity intelligence (optional) ---------------
    # Present when infrastructure proximity data is available; None otherwise.
    nearest_facility_name: Optional[str] = None
    nearest_facility_type: Optional[str] = None
    nearest_facility_distance_m: Optional[float] = None
    nearby_facility_count: Optional[int] = None
    industrial_proximity_score: Optional[float] = None
    near_critical_infrastructure: Optional[bool] = None

    # --- Explainable event classification (always produced) -----------
    event_type: EventType
    classification_confidence: float
    classification_reasons: List[str]
    matched_signals: Dict[str, Any]
    classification_score_breakdown: Dict[str, Any]
    disclaimer: str


class HotspotListResponse(BaseModel):
    hotspots: List[Hotspot]