from pydantic import BaseModel
from typing import List


class Hotspot(BaseModel):
    id: str
    latitude: float
    longitude: float
    detected_at: str
    brightness: float
    frp: float
    confidence: float


class HotspotListResponse(BaseModel):
    hotspots: List[Hotspot]