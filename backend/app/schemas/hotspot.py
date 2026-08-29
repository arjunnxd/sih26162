from pydantic import BaseModel
from typing import List, Literal


RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
AnomalyLevel = Literal["NORMAL", "UNUSUAL", "HIGHLY_UNUSUAL"]
PriorityLevel = Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]


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


class HotspotListResponse(BaseModel):
    hotspots: List[Hotspot]