"""Deterministic mock/demo thermal data source provider.

Simulates a FIRMS-style satellite feed so the ingestion architecture can be
exercised without network access. The records intentionally use the *naming
conventions of a real provider* (``acq_date``/``acq_time``, ``bright_ti4``,
``frp``, ``confidence`` as 0-100, ``satellite``/``instrument``, ``daynight``)
so the normalizer gets realistic input to flatten.

This is demo data only - it must not be mistaken for live satellite detections.

Callers can also request a documented set of intentionally-bad edge case
records (``include_edge_cases=True``) to exercise the normalizer's safe-skip
behaviour.
"""

from __future__ import annotations

from typing import Any, Optional

from app.services.data_sources.provider import Provider

# Determininistic FIRMS-like payload. All records here are normalizable.
DEFAULT_RECORDS: list[dict] = [
    {
        "key": "VNP14IMGTDL_NRT_2026001",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "acq_date": "2026-01-15",
        "acq_time": "1030",
        "satellite": "NPP",
        "instrument": "VIIRS",
        "brightness": 320.5,
        "frp": 45.2,
        "confidence": 92,
        "daynight": "D",
        "version": "1.0",
    },
    {
        "id": "firms_demo_002",
        "lat": 19.0760,
        "lon": 72.8777,
        "timestamp": "2026-01-15 11:15:00",
        "bright_ti4": 310.8,
        "fire_radiative_power": "38.7",
        "confidence": "88%",
        "sat": "NOAA-20",
        "instrument": "VIIRS",
    },
    {
        "latitude": 12.9716,
        "longitude": 77.5946,
        "detected_at": "2026-01-15T12:00:00Z",
        "confidence": "high",
        "demo_flag": "recurring-candidate",
    },
    {
        "hotspot_id": "firms_demo_004",
        "latitude": 21.0,
        "lng": 79.0,
        "date": "2026-01-14",
        "frp": 12.5,
        "confidence": 0.73,
    },
    {
        "uid": "firms_demo_005",
        "latitude": 13.05,
        "longitude": 77.57,
        "scan_date": "2026-01-13",
        "scan_time": "1835",
        "bright_ti4": 299.1,
        "frp": "20.9",
        "confidence": 61,
        "daynight": "N",
    },
]

# Documented intentionally-bad records used to exercise safe-skip behaviour.
EDGE_CASE_RECORDS: list[dict] = [
    {"latitude": 95.0, "longitude": 77.0, "frp": 10.0},          # invalid lat
    {"latitude": 28.0, "longitude": 200.0, "frp": 10.0},         # invalid lon
    {"latitude": "abc", "longitude": 77.0, "frp": 10.0},         # non-numeric lat
    {"frp": 10.0},                                               # missing coords
    {
        "latitude": 28.0,
        "longitude": 77.0,
        "frp": float("nan"),           # invalid number
        "brightness": -5.0,            # negative -> rejected
        "confidence": "n/a",           # non-numeric confidence
        "timestamp": "not-a-date",     # unparseable timestamp
    },
    "not-a-dict",                       # malformed record
]


class MockFirmsProvider(Provider):
    """Demo adapter returning the same structure a future real provider would.

    - ``fetch_raw(include_edge_cases=True)`` also returns intentionally
      invalid records so normalization skipping can be demonstrated.
    - No network access is used; output is fully deterministic.
    """

    name = "mock_firms"
    description = (
        "Deterministic FIRMS-style demo feed for testing the ingestion layer"
    )
    metadata = {
        "source": "NASA_FIRMS_MOCK",
        "provider": "mock_firms",
        "satellite": "SNPP",
        "instrument": "VIIRS",
    }

    def fetch_raw(self, include_edge_cases: bool = False, **kwargs: Any) -> list[dict]:
        if include_edge_cases:
            return list(DEFAULT_RECORDS) + list(EDGE_CASE_RECORDS)
        return list(DEFAULT_RECORDS)