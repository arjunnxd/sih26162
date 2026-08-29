from fastapi import APIRouter
from app.schemas.hotspot import HotspotListResponse

router = APIRouter()


@router.get("/api/hotspots", response_model=HotspotListResponse)
async def get_hotspots():
    mock_hotspots = [
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
    return HotspotListResponse(hotspots=mock_hotspots)