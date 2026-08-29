"""Infrastructure proximity intelligence for the SIH26162 prototype.

Independent module: it loads the mock infrastructure dataset from
``app/data/infrastructure.json`` and enriches any coordinate with proximity
intelligence using :mod:`app.services.geospatial_service`.

ARCHITECTURE
------------
    geospatial_service.calculate_distance_m(...)
                          ^
                          |
    proximity_service.analyze_infrastructure_proximity(lat, lon)
                          |
                          +--> load_infrastructure_facilities()
                          +--> calculate_industrial_proximity_score(...)

This module is deliberately NOT wired into the existing hotspot API / analysis
pipeline yet. Member 1 integrates it after external verification.

SCORING (deterministic, always 0-100, explainable, no randomness)
----------------------------------------------------------------
Final score = base_nearest_distance_score + nearby_count_bonus + critical_bonus,
clamped to [0, 100].

1. Base score from distance to the NEAREST facility (0-75), obtained by
   linear interpolation between documented anchor points:

       nearest distance (m)     base score     meaning
       -------------------     ----------     -------
       0                        75.0           very close  (highest contribution)
       1,000                    60.0           close       (high)
       5,000                    45.0           moderate    (medium)
       15,000                   30.0           far         (low)
       50,000                   15.0           very far    (near zero)
       150,000+                 0.0            beyond      (zero)

2. Nearby-count bonus (0-15): +5 per facility within NEARBY_RADIUS_M,
   capped at NEARBY_COUNT_BONUS_MAX.

3. Critical-infrastructure bonus (+10): applied when an ``is_critical``
   facility lies within CRITICAL_DISTANCE_M of the query point.

ERROR HANDLING (safe structured results, never crash)
-----------------------------------------------------
* invalid latitude / longitude        -> structured result with ``error`` set
                                          and all values at safe defaults
* missing infrastructure file         -> ``error`` = "no_facilities_available"
* empty infrastructure dataset        -> ``error`` = "no_facilities_available"
* no facilities found (all invalid)   -> ``error`` = "no_facilities_available"
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from app.services.geospatial_service import (
    calculate_distance_m,
    is_valid_coordinates,
)

DEFAULT_INFRASTRUCTURE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "infrastructure.json"
)


class ProximityThresholds:
    """Configurable thresholds for proximity intelligence.

    All distances are in meters. Every constant is deterministic and
    documented so the resulting score is explainable.
    """

    # Radius definitions
    NEARBY_RADIUS_M = 20_000  # facilities within this radius count as "nearby"
    CRITICAL_DISTANCE_M = 10_000  # critical facility inside this radius -> near critical

    # Base distance -> score anchors (linear interpolation), meters -> 0-75
    NEAREST_SCORE_ANCHORS = (
        (0.0, 75.0),      # very close  -> highest contribution
        (1_000.0, 60.0),  # close       -> high
        (5_000.0, 45.0),  # moderate    -> medium
        (15_000.0, 30.0), # far         -> low
        (50_000.0, 15.0), # very far    -> near zero
        (150_000.0, 0.0), # beyond      -> zero
    )

    # Bonuses (additive; final score is clamped to [0, 100])
    NEARBY_COUNT_BONUS_PER_FACILITY = 5.0
    NEARBY_COUNT_BONUS_MAX = 15.0
    CRITICAL_BONUS = 10.0


def load_infrastructure_facilities(
    infrastructure_path: Optional[str | os.PathLike] = None,
) -> list[dict]:
    """Load facility records from a JSON file.

    Safety behaviour:
      * Missing / unreadable file ........ returns ``[]``
      * Malformed JSON ................... returns ``[]``
      * Missing ``facilities`` list ...... returns ``[]``
      * Individual bad records ............ skipped (missing fields or
                                         invalid coordinates)

    Expected record shape::

        {
            "id": str,
            "name": str,
            "type": str,
            "latitude": float,
            "longitude": float,
            "is_critical": bool
        }

    Args:
        infrastructure_path: optional explicit path to the JSON dataset.
            Defaults to ``backend/app/data/infrastructure.json``.

    Returns:
        List of validated facility dicts, in file order.
    """
    path = Path(infrastructure_path) if infrastructure_path else DEFAULT_INFRASTRUCTURE_PATH

    if not path.exists() or not path.is_file():
        return []

    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (json.JSONDecodeError, OSError):
        return []

    raw_facilities = payload.get("facilities", []) if isinstance(payload, dict) else payload
    if not isinstance(raw_facilities, list):
        return []

    required_fields = ("id", "name", "type", "latitude", "longitude", "is_critical")

    facilities = []
    for record in raw_facilities:
        if not isinstance(record, dict):
            continue
        if not all(field in record for field in required_fields):
            continue
        if not is_valid_coordinates(record.get("latitude"), record.get("longitude")):
            continue
        facilities.append(record)

    return facilities
def _distance_score_for_nearest(distance_m: Optional[float]) -> float:
    """Base score (0-75) from the nearest-facility distance via interpolation."""
    if distance_m is None:
        return 0.0

    anchors = ProximityThresholds.NEAREST_SCORE_ANCHORS
    if distance_m >= anchors[-1][0]:
        return 0.0

    for (d_lo, s_lo), (d_hi, s_hi) in zip(anchors, anchors[1:]):
        if d_lo <= distance_m <= d_hi:
            span = d_hi - d_lo
            if span <= 0:
                return s_lo
            fraction = (distance_m - d_lo) / span
            return s_lo + (s_hi - s_lo) * fraction

    return 0.0


def calculate_industrial_proximity_score(
    nearest_distance_m: Optional[float],
    nearby_facility_count: int,
    near_critical_infrastructure: bool,
) -> float:
    """Deterministic 0-100 industrial-proximity score.

    Args:
        nearest_distance_m: distance (m) to the nearest facility, or ``None``
            when no facility is available.
        nearby_facility_count: number of facilities inside NEARBY_RADIUS_M.
        near_critical_infrastructure: critical facility inside
            CRITICAL_DISTANCE_M.

    Returns:
        Score clamped to [0.0, 100.0] and rounded to 2 decimals.
    """
    base = _distance_score_for_nearest(nearest_distance_m)

    count_bonus = min(
        nearby_facility_count * ProximityThresholds.NEARBY_COUNT_BONUS_PER_FACILITY,
        ProximityThresholds.NEARBY_COUNT_BONUS_MAX,
    )

    critical_bonus = (
        ProximityThresholds.CRITICAL_BONUS if near_critical_infrastructure else 0.0
    )

    total = base + count_bonus + critical_bonus
    total = max(0.0, min(100.0, total))
    return round(total, 2)


def _safe_proximity_result(latitude: float, longitude: float, error: str) -> dict:
    """Return a safe, zeroed proximity result used for all degraded cases."""
    return {
        "latitude": latitude,
        "longitude": longitude,
        "nearest_facility_name": None,
        "nearest_facility_type": None,
        "nearest_facility_distance_m": None,
        "nearby_facility_count": 0,
        "industrial_proximity_score": 0.0,
        "near_critical_infrastructure": False,
        "nearby_facilities": [],
        "nearest_critical_facility": None,
        "nearest_critical_distance_m": None,
        "score_breakdown": {
            "base_nearest_distance_score": 0.0,
            "nearby_count_bonus": 0.0,
            "critical_bonus": 0.0,
        },
        "error": error,
    }
def analyze_infrastructure_proximity(
    latitude: float,
    longitude: float,
    infrastructure_path: Optional[str | os.PathLike] = None,
) -> dict:
    """Main proximity-intelligence entrypoint (used by future integrators).

    Args:
        latitude: query latitude in decimal degrees.
        longitude: query longitude in decimal degrees.
        infrastructure_path: optional explicit dataset path (testing/debug).

    Returns:
        Structured dict (never raises for data problems)::

            {
                "latitude": float,
                "longitude": float,
                "nearest_facility_name": str | None,
                "nearest_facility_type": str | None,
                "nearest_facility_distance_m": float | None,
                "nearby_facility_count": int,
                "industrial_proximity_score": float,   # always 0..100
                "near_critical_infrastructure": bool,
                "nearby_facilities": [                  # sorted by distance
                    {"id", "name", "type", "critical", "distance_m"}
                ],
                "nearest_critical_facility": str | None,
                "nearest_critical_distance_m": float | None,
                "score_breakdown": {
                    "base_nearest_distance_score": float,
                    "nearby_count_bonus": float,
                    "critical_bonus": float,
                },
                "error": str | None,
            }

        Invalid coordinates or unavailable facilities produce a safe zeroed
        result with ``error`` describing the cause.
    """
    if not is_valid_coordinates(latitude, longitude):
        return _safe_proximity_result(latitude, longitude, "invalid_coordinates")

    facilities = load_infrastructure_facilities(infrastructure_path)
    if not facilities:
        return _safe_proximity_result(latitude, longitude, "no_facilities_available")

    nearby: list[dict] = []
    nearest: Optional[dict] = None
    nearest_critical: Optional[dict] = None

    for facility in facilities:
        distance_m = calculate_distance_m(
            latitude, longitude, facility["latitude"], facility["longitude"]
        )
        if distance_m is None:
            continue

        entry = {
            "id": facility["id"],
            "name": facility["name"],
            "type": facility["type"],
            "critical": bool(facility.get("is_critical", False)),
            "distance_m": round(distance_m, 2),
        }
        nearby.append(entry)

        if nearest is None or distance_m < nearest["distance_m"]:
            nearest = entry
        if entry["critical"] and (
            nearest_critical is None or distance_m < nearest_critical["distance_m"]
        ):
            nearest_critical = entry

    if nearest is None:
        return _safe_proximity_result(latitude, longitude, "no_facilities_available")

    nearby.sort(key=lambda entry: entry["distance_m"])

    nearby_count = sum(
        1 for entry in nearby
        if entry["distance_m"] <= ProximityThresholds.NEARBY_RADIUS_M
    )
    near_critical = (
        nearest_critical is not None
        and nearest_critical["distance_m"] <= ProximityThresholds.CRITICAL_DISTANCE_M
    )

    score = calculate_industrial_proximity_score(
        nearest_distance_m=nearest["distance_m"],
        nearby_facility_count=nearby_count,
        near_critical_infrastructure=near_critical,
    )

    return {
        "latitude": latitude,
        "longitude": longitude,
        "nearest_facility_name": nearest["name"],
        "nearest_facility_type": nearest["type"],
        "nearest_facility_distance_m": nearest["distance_m"],
        "nearby_facility_count": nearby_count,
        "industrial_proximity_score": score,
        "near_critical_infrastructure": near_critical,
        "nearby_facilities": nearby,
        "nearest_critical_facility": (
            nearest_critical["name"] if nearest_critical is not None else None
        ),
        "nearest_critical_distance_m": (
            nearest_critical["distance_m"] if nearest_critical is not None else None
        ),
        "score_breakdown": {
            "base_nearest_distance_score": round(
                _distance_score_for_nearest(nearest["distance_m"]), 2
            ),
            "nearby_count_bonus": round(
                min(
                    nearby_count * ProximityThresholds.NEARBY_COUNT_BONUS_PER_FACILITY,
                    ProximityThresholds.NEARBY_COUNT_BONUS_MAX,
                ),
                2,
            ),
            "critical_bonus": (
                ProximityThresholds.CRITICAL_BONUS if near_critical else 0.0
            ),
        },
        "error": None,
    }