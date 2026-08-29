from fastapi import APIRouter, HTTPException
from app.schemas.hotspot import Hotspot, HotspotListResponse
from app.services.hotspot_analysis_service import analyze_hotspot, get_mock_hotspots, find_raw_hotspot

router = APIRouter()


@router.get("/api/hotspots", response_model=HotspotListResponse)
async def get_hotspots():
    mock_hotspots = get_mock_hotspots()
    analyzed_hotspots = [analyze_hotspot(hotspot) for hotspot in mock_hotspots]
    return HotspotListResponse(hotspots=analyzed_hotspots)


@router.get("/api/hotspots/{hotspot_id}", response_model=Hotspot)
async def get_hotspot(hotspot_id: str):
    raw_hotspot = find_raw_hotspot(hotspot_id)
    if raw_hotspot is None:
        raise HTTPException(
            status_code=404,
            detail=f"Hotspot with id '{hotspot_id}' not found"
        )
    
    analyzed_hotspot = analyze_hotspot(raw_hotspot)
    return Hotspot(**analyzed_hotspot)