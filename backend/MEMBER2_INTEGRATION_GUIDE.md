# Member 2 — Backend Integration Guide

Verified end-to-end on the `analysis` branch (29/29 integration checks passed).
All modules are stdlib-only: no FastAPI, no Pydantic, no network calls.

## Integration flow

```
Provider  ->  Normalization  ->  Data Quality + Deduplication
         ->  Accepted Hotspots  ->  to_pipeline_dict()  ->  analyze_hotspot()
```

## 1. Fetch + normalize

```python
from app.services.data_sources import build_provider

provider = build_provider("mock_firms")            # or "firms"
normalized, dropped = provider.fetch_hotspots_with_dropped()
# normalized: list[NormalizedHotspot]; dropped: list[{record, reason}]
```

## 2. Quality + deduplication

```python
from app.services.data_quality import process_hotspots

result = process_hotspots(normalized)
result.accepted    # original input objects (valid + unique)
result.duplicates  # DuplicateMatch(record, category, similarity_score, reasons, duplicate_of)
result.rejected    # [{"record", "reason", "quality"}]
result.summary     # total_input / accepted_count / duplicate_count / rejected_count / quality_levels
```

Accepts `NormalizedHotspot` objects, `to_dict()` dicts, `to_pipeline_dict()`
dicts, and plain provider dicts. Thresholds are configurable via
`QualityConfig` and `DeduplicationConfig`.

## 3. Hand off to the centralized pipeline

```python
for hotspot in result.accepted:
    pipeline_input = hotspot.to_pipeline_dict()
    # exactly: id, latitude, longitude, detected_at, brightness, frp, confidence
    analyzed = analyze_hotspot(pipeline_input)   # Member 1's pipeline
```

`NormalizedHotspot.to_pipeline_dict()` is directly compatible with
`analyze_hotspot(raw_hotspot)` — verified by execution.

## 4. Optional intelligence enrichment (post-analysis)

```python
from app.services.proximity_service import analyze_infrastructure_proximity
from app.services.classification_service import classify_thermal_event_from_signals

proximity = analyze_infrastructure_proximity(lat, lon)
signals = {**analyzed, **proximity}                # merge analysis + proximity
event = classify_thermal_event_from_signals(signals)
# -> event_type, classification_confidence, classification_reasons,
#    matched_signals, classification_score_breakdown, disclaimer
```

## Notes for Member 1

- Member 1 should inspect the current centralized pipeline
  (`hotspot_analysis_service.get_mock_hotspots`) before replacing existing
  mock hotspot loading with `build_provider(...) -> process_hotspots(...)`.
- `build_provider("firms")` requires `FIRMS_BASE_URL` (and `FIRMS_API_KEY`)
  to be configured; without them it raises `ProviderError` by design.
- The `firms` provider performs live network calls only when configured —
  keep using `mock_firms` for demos and tests.
