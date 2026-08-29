"""Explainable data-quality analysis for normalized thermal hotspot records.

Deterministic, stdlib-only scoring. A component earns its configured weight
only when its value is present AND valid; missing values contribute 0 and are
reported in ``missing_fields`` - no intelligence is ever fabricated.

INVALID RECORDS
---------------
A record is INVALID (score forced to 0) when its coordinates are missing
entirely or present but invalid. Coordinates are the one field the downstream
geospatial pipeline cannot work without. Invalid timestamps or invalid thermal
values reduce the score and are reported, but do not invalidate the record.

TEXTUAL CONFIDENCE
------------------
Confidence labels such as "high"/"nominal" are legitimate source information.
They are reported via a warning and never converted into a fake numeric value.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.services.data_quality.models import (
    QUALITY_INVALID,
    QualityAssessment,
    QualityConfig,
)

#: Core fields assessed for completeness (matches the pipeline contract).
CORE_FIELDS: Tuple[str, ...] = (
    "id",
    "latitude",
    "longitude",
    "detected_at",
    "brightness",
    "frp",
    "confidence",
)

#: Timestamp formats accepted in addition to ISO-8601 (attempted in order).
_TIMESTAMP_FORMATS = (
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
)


def finite_float(value: Any) -> Optional[float]:
    """Coerce ``value`` to a finite float, or return ``None``.

    Rejects booleans, non-numeric strings, ``NaN`` and ``+-Infinity``.
    Numeric strings (e.g. ``"45.2"``) are accepted - providers sometimes
    deliver numbers as strings and this is a value-preserving conversion,
    not a fabrication.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value.strip())
        except (TypeError, ValueError):
            return None
    else:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def parse_timestamp_epoch(value: Any) -> Optional[float]:
    """Parse a detection timestamp to POSIX seconds, or return ``None``.

    Accepts ``datetime`` objects, ISO-8601 strings (``Z`` or numeric offsets),
    and a few common fallback formats. Naive datetimes are interpreted as UTC.
    Unparseable input never raises.
    """
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
        dt = None
        try:
            dt = datetime.fromisoformat(candidate)
        except ValueError:
            for fmt in _TIMESTAMP_FORMATS:
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
        if dt is None:
            return None
    else:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _clean_id(value: Any) -> Optional[str]:
    """Return a non-empty string id, or ``None`` when absent/blank."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def assess_quality(
    record: Any,
    config: Optional[QualityConfig] = None,
) -> QualityAssessment:
    """Assess the data quality of one hotspot record deterministically.

    ``record`` must be a mapping-like dict (canonical form). Non-dict input
    yields an INVALID assessment rather than raising, so batch processing
    never crashes on a single malformed entry.
    """
    config = config or QualityConfig()
    record = record if isinstance(record, dict) else {}

    reasons: List[str] = []
    warnings: List[str] = []
    missing: List[str] = []
    invalid: List[str] = []
    usable: Dict[str, bool] = {}

    # -- Coordinates (weight split evenly across the two axes) ---------------
    half_weight = config.weight_coordinates / 2.0
    lat_raw = record.get("latitude")
    lon_raw = record.get("longitude")
    lat = finite_float(lat_raw)
    lon = finite_float(lon_raw)
    lat_valid = lat is not None and -90.0 <= lat <= 90.0
    lon_valid = lon is not None and -180.0 <= lon <= 180.0

    if lat_valid:
        usable["latitude"] = True
    elif lat_raw is None:
        missing.append("latitude")
    else:
        invalid.append("latitude")
        warnings.append("Latitude is invalid (non-numeric, NaN, or out of range)")

    if lon_valid:
        usable["longitude"] = True
    elif lon_raw is None:
        missing.append("longitude")
    else:
        invalid.append("longitude")
        warnings.append("Longitude is invalid (non-numeric, NaN, or out of range)")

    if lat_valid and lon_valid:
        score = config.weight_coordinates
        reasons.append("Coordinates are valid")
    else:
        score = (half_weight if lat_valid else 0.0) + (half_weight if lon_valid else 0.0)

    # -- Timestamp ------------------------------------------------------------
    ts_raw = record.get("detected_at")
    epoch = parse_timestamp_epoch(ts_raw)
    if ts_raw is None:
        missing.append("detected_at")
        warnings.append("Detection timestamp is unavailable")
    elif epoch is None:
        invalid.append("detected_at")
        warnings.append("Detection timestamp is unparseable")
    else:
        usable["detected_at"] = True
        score += config.weight_timestamp
        reasons.append("Detection timestamp is available")

    # -- Thermal values (optional; invalid values never fabricate data) -------
    for name, label, weight in (
        ("brightness", "Brightness", config.weight_brightness),
        ("frp", "FRP", config.weight_frp),
    ):
        raw = record.get(name)
        if raw is None:
            missing.append(name)
            reasons.append(f"{label} value is unavailable")
            continue
        number = finite_float(raw)
        if number is None:
            invalid.append(name)
            warnings.append(f"{label} value is invalid (non-numeric, NaN, or Infinity)")
            continue
        usable[name] = True
        score += weight
        reasons.append(f"{label} value is available")

    # -- Confidence -------------------------------------------------------------
    conf_raw = record.get("confidence")
    if conf_raw is None:
        missing.append("confidence")
        reasons.append("Confidence value is missing")
    else:
        conf = finite_float(conf_raw)
        if conf is None:
            # A textual label (e.g. "high") is preserved information, not an
            # invalid value - warn but never invent a number.
            warnings.append(
                "Confidence is a textual label; it is not converted into "
                "a fabricated numeric confidence"
            )
        else:
            usable["confidence"] = True
            score += config.weight_confidence
            reasons.append("Confidence value is available")
            if not 0.0 <= conf <= 1.0:
                warnings.append("Confidence is outside the normalized 0..1 range")

    # -- Identifier ---------------------------------------------------------------
    record_id = _clean_id(record.get("id"))
    if record_id is None:
        missing.append("id")
        warnings.append("Record identifier is missing")
    else:
        usable["id"] = True
        score += config.weight_id
        reasons.append("Record identifier is available")

    # -- Completeness ---------------------------------------------------------------
    completeness = round(
        sum(1 for name in CORE_FIELDS if usable.get(name)) / len(CORE_FIELDS), 4
    )
    if any(name in missing for name in ("brightness", "frp")):
        warnings.append("Record has incomplete thermal information")

    # -- Invalidity rule --------------------------------------------------------------
    coords_unusable = bool(set(invalid) & {"latitude", "longitude"}) or (
        "latitude" in missing and "longitude" in missing
    )
    is_valid = not coords_unusable
    if coords_unusable:
        score = 0.0
        reasons.insert(0, "Record is invalid: coordinates are missing or invalid")

    final_score = round(max(0.0, min(100.0, score)), 2)
    return QualityAssessment(
        quality_score=final_score,
        quality_level=config.level_for(final_score),
        quality_reasons=reasons,
        quality_warnings=warnings,
        missing_fields=missing,
        invalid_fields=invalid,
        completeness_ratio=completeness,
        is_valid=is_valid,
    )


def assess_quality_batch(
    records: Iterable[Any],
    config: Optional[QualityConfig] = None,
) -> List[QualityAssessment]:
    """Assess many records, preserving input order (deterministic)."""
    config = config or QualityConfig()
    return [assess_quality(record, config) for record in records]

