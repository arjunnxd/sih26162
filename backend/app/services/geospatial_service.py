"""Geospatial utilities for the SIH26162 intelligence layer.

Standard-library-only geographic helpers. No geopandas, no shapely.

VALIDATION CONTRACT
-------------------
* ``calculate_distance_m`` validates every coordinate before computing.
* An invalid latitude (outside -90..90) or longitude (outside -180..180)
  does NOT raise: it returns ``None`` (a safe result) so callers can degrade
  gracefully. Use ``is_valid_coordinates`` when validation itself is needed.
* Valid coordinates always return a non-negative float distance in meters.

EARTH MODEL
-----------
Uses a mean Earth radius of 6,371,000 m and the Haversine formula:

    a = sin(dlat/2)^2 + cos(lat1) * cos(lat2) * sin(dlon/2)^2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance_m = R * c

Accurate to ~0.5% over the short/medium distances used in this prototype.
"""

from __future__ import annotations

import math
from typing import Optional

EARTH_RADIUS_M = 6_371_000.0  # mean Earth radius (meters)

LATITUDE_MIN = -90.0
LATITUDE_MAX = 90.0
LONGITUDE_MIN = -180.0
LONGITUDE_MAX = 180.0


def is_valid_latitude(latitude: float) -> bool:
    """Return True when ``latitude`` can be coerced to a number in [-90, 90]."""
    try:
        latitude = float(latitude)
    except (TypeError, ValueError):
        return False
    return LATITUDE_MIN <= latitude <= LATITUDE_MAX


def is_valid_longitude(longitude: float) -> bool:
    """Return True when ``longitude`` can be coerced to a number in [-180, 180]."""
    try:
        longitude = float(longitude)
    except (TypeError, ValueError):
        return False
    return LONGITUDE_MIN <= longitude <= LONGITUDE_MAX


def is_valid_coordinates(latitude: float, longitude: float) -> bool:
    """Return True when both latitude and longitude are valid."""
    return is_valid_latitude(latitude) and is_valid_longitude(longitude)


def calculate_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> Optional[float]:
    """Great-circle distance between two coordinates (Haversine), in meters.

    Args:
        lat1, lon1: first coordinate in decimal degrees.
        lat2, lon2: second coordinate in decimal degrees.

    Returns:
        Distance in meters as a ``float``, or ``None`` when any coordinate is
        invalid. Invalid input never raises (safe result contract).

    Examples:
        >>> calculate_distance_m(0.0, 0.0, 0.0, 0.0)
        0.0
        >>> calculate_distance_m(91.0, 0.0, 0.0, 0.0) is None
        True
    """
    if not is_valid_coordinates(lat1, lon1) or not is_valid_coordinates(lat2, lon2):
        return None

    lat1 = float(lat1)
    lon1 = float(lon1)
    lat2 = float(lat2)
    lon2 = float(lon2)

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    # Guard against floating-point drift outside [0, 1].
    a = max(0.0, min(1.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return EARTH_RADIUS_M * c


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> Optional[float]:
    """Wrapper around :func:`calculate_distance_m` returning kilometers.

    Returns ``None`` for invalid coordinates (same safe contract as the
    meter-level function).
    """
    distance_m = calculate_distance_m(lat1, lon1, lat2, lon2)
    if distance_m is None:
        return None
    return round(distance_m / 1000.0, 3)