"""Generic thermal hotspot normalization layer.

Converts raw provider records (in any field nomenclature) into the common
:class:`NormalizedHotspot` format. Provider-independent, deterministic, and
safe - never raises for bad values, never invents intelligence values, and
drops records whose coordinates are missing/invalid (callers receive a list
of dropped records with reasons).

Safety contract
---------------
* Invalid/missing coordinates  -> record DROPPED (reason: ``invalid_coordinates``)
* Invalid numeric values       -> field becomes ``None``; record survives
* Textual confidence           -> never converted to a fake number; the raw
  label is preserved as ``extra_fields["confidence_label"]``
* Confidence already 0..1      -> kept as-is
* Confidence given 0..100      -> divided by 100 (documented unit normalization)
* Missing id                   -> deterministic placeholder id generated from
  source + coordinates + timestamp (flagged in extra_fields)
* Unknown extra fields         -> preserved in ``extra_fields``
* Unparseable timestamp        -> ``detected_at`` becomes ``None``; record survives

Uses only the Python standard library plus the shared coordinate validator
from ``app.services.geospatial_service``.
"""

from __future__ import annotations

import datetime as _dt
import math
import re

from app.services.data_sources.models import NormalizedHotspot
from app.services.geospatial_service import is_valid_coordinates

# --------------------------------------------------------------------------
# Field alias tables (canonical -> accepted names, priority order)
# --------------------------------------------------------------------------
ALIASES = {
    "id": ("id", "hotspot_id", "event_id", "key", "uid"),
    "latitude": ("latitude", "lat"),
    "longitude": ("longitude", "lon", "lng", "long"),
    "detected_at": ("detected_at", "detected", "datetime", "timestamp", "date"),
    "brightness": ("brightness", "bright_ti4", "brightness_ti4", "bt"),
    "frp": ("frp", "fire_radiative_power", "frp_mw", "radiative_power"),
    "confidence": ("confidence", "conf", "confidence_level"),
    "source": ("source", "data_source"),
    "satellite": ("satellite", "sat"),
    "instrument": ("instrument",),
    "provider": ("provider", "feed"),
}

# Data/time field pairs joined to build detected_at (FIRMS-style and variants).
_ACQ_DATE = "acq_date"
_ACQ_TIME = "acq_time"
_ACQ_PAIRS = (
    ("acq_date", "acq_time"),
    ("scan_date", "scan_time"),
)

# Extra timestamp formats after ISO-8601 handling.
_EXTRA_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
)

_HHMM_RE = re.compile(r"^([01]\d|2[0-3])[0-5]\d$")

# Textual confidence labels - preserved as-is, never converted to numbers.
_TEXTUAL_CONFIDENCE = {"high", "nominal", "low", "medium"}


def _as_float(value):
    """Coerce a value to float, or return ``None``.

    Rejects None, booleans, non-numeric strings and non-finite numbers.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            value = float(text)
        except ValueError:
            return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number

def _extract(record: dict, aliases: tuple) -> object:
    """Return the first present alias value (case-insensitive, by priority)."""
    for alias in aliases:
        for key, value in record.items():
            if isinstance(key, str) and key.lower() == alias.lower():
                return value
    return None


def _parse_to_utc_iso(value) -> Optional[str]:
    """Parse a timestamp and return ``YYYY-MM-DDTHH:MM:SSZ`` (UTC).

    Returns ``None`` for unparseable values. Naive timestamps are assumed UTC.
    """
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text:
        return None

    dt = None
    iso_text = text.replace("Z", "+00:00") if text.endswith("Z") else text
    try:
        dt = _dt.datetime.fromisoformat(iso_text)
    except ValueError:
        pass

    if dt is None:
        for fmt in _EXTRA_TIMESTAMP_FORMATS:
            try:
                dt = _dt.datetime.strptime(text, fmt)
                break
            except ValueError:
                continue

    if dt is None:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    else:
        dt = dt.astimezone(_dt.timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_acq_datetime(record: dict):
    """Join a paired date/time field set (e.g. acq_date+acq_time, HHMM time).

    Returns ``(iso_string_or_None, used_pairs_or_None)`` where ``used_pairs``
    is the tuple of field names consumed, enabling full transparency.
    """
    for date_key, time_key in _ACQ_PAIRS:
        date_value = _extract(record, (date_key,))
        time_value = _extract(record, (time_key,))
        if date_value is None:
            continue
        date_part = str(date_value).strip()
        time_part = str(time_value).strip() if time_value is not None else None
        if not date_part:
            continue
        if time_part and _HHMM_RE.match(time_part):
            time_part = f"{time_part[:2]}:{time_part[2:]}"
        elif time_part and ":" not in time_part:
            time_part = None
        combined = f"{date_part} {time_part}" if date_part and time_part else date_part
        parsed = _parse_to_utc_iso(combined)
        if parsed is not None:
            return parsed, (date_key, time_key)
    return None, None


def _normalize_confidence(value) -> tuple[Optional[float], dict]:
    """Convert confidence to 0..1 while preserving the original value.

    Returns ``(confidence, notes)``:
    * numeric 0..1     -> kept as-is
    * numeric 0..100   -> divided by 100 (documented unit normalization)
    * textual label    -> ``confidence`` None; ``confidence_label`` preserved
    * anything else    -> ``confidence`` None; ``confidence_raw`` preserved
    """
    notes: dict = {}
    if isinstance(value, bool):
        return None, notes

    if isinstance(value, str):
        label = value.strip().lower()
        if label in _TEXTUAL_CONFIDENCE:
            notes["confidence_label"] = value.strip()
            return None, notes
        parsed = _as_float(value)
        if parsed is None and value.strip().endswith("%"):
            parsed = _as_float(value.strip()[:-1])
        if parsed is None:
            notes["confidence_raw"] = value
            return None, notes
        value = parsed
    else:
        parsed = _as_float(value)
        if parsed is None:
            return None, notes
        value = parsed

    notes["confidence_raw"] = value
    if 0.0 <= value <= 1.0:
        return round(value, 4), notes
    if 1.0 < value <= 100.0:
        return round(value / 100.0, 4), notes
    return None, notes


def _generate_id(latitude: float, longitude: float, detected_at: Optional[str]) -> str:
    """Deterministic placeholder id when the source provides none."""
    raw = f"{latitude:.5f}|{longitude:.5f}|{detected_at or 'no_timestamp'}"
    sanitized = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_")
    return sanitized or "hotspot_unknown"


def _matched_key(record: dict, aliases: tuple):
    """Return the actual record key matched by any alias, or ``None``."""
    for alias in aliases:
        for key in record:
            if isinstance(key, str) and key.lower() == alias.lower():
                return key
    return None


def _extra_fields(record: dict, consumed_keys: set) -> dict:
    """Collect non-consumed provider fields, sorted for determinism."""
    preserved = {
        key: value
        for key, value in record.items()
        if (not isinstance(key, str)) or (key not in consumed_keys)
    }
    return dict(sorted(preserved.items(), key=lambda item: str(item[0])))


def normalize_record(record, metadata: Optional[dict] = None) -> Optional[NormalizedHotspot]:
    """Normalize a single raw provider record.

    Returns ``None`` when the record is not a dict or its coordinates are
    missing/invalid (the caller should treat it as *dropped*). Never raises
    for bad values.
    """
    if not isinstance(record, dict):
        return None

    latitude = _as_float(_extract(record, ALIASES["latitude"]))
    longitude = _as_float(_extract(record, ALIASES["longitude"]))
    if latitude is None or longitude is None or not is_valid_coordinates(latitude, longitude):
        return None

    # detected_at: explicit field first, then paired date/time fields.
    detected_at_explicit = _parse_to_utc_iso(_extract(record, ALIASES["detected_at"]))
    detected_at = detected_at_explicit
    used_time_pair = None
    if detected_at is None:
        detected_at, used_time_pair = _parse_acq_datetime(record)

    frp_raw = _extract(record, ALIASES["frp"])
    frp = _as_float(frp_raw)
    frp_note = None
    if frp is not None and frp < 0.0:
        frp = None
        frp_note = "frp_rejected_negative"
    elif frp_raw is not None and frp is None:
        frp_note = "frp_invalid"

    brightness_raw = _extract(record, ALIASES["brightness"])
    brightness = _as_float(brightness_raw)
    brightness_note = None
    if brightness is not None and brightness < 0.0:
        brightness = None
        brightness_note = "brightness_rejected_negative"
    elif brightness_raw is not None and brightness is None:
        brightness_note = "brightness_invalid"

    confidence, confidence_notes = _normalize_confidence(
        _extract(record, ALIASES["confidence"])
    )

    raw_id = _extract(record, ALIASES["id"])
    id_generated = raw_id is None or not str(raw_id).strip()
    hotspot_id = (
        _generate_id(latitude, longitude, detected_at) if id_generated else str(raw_id).strip()
    )

    meta = metadata or {}
    source = _extract(record, ALIASES["source"]) or meta.get("source")
    satellite = _extract(record, ALIASES["satellite"]) or meta.get("satellite")
    instrument = _extract(record, ALIASES["instrument"]) or meta.get("instrument")
    provider = _extract(record, ALIASES["provider"]) or meta.get("provider")

    # Determine which original keys were consumed by alias resolution.
    consumed_keys = set()
    for aliases in ALIASES.values():
        matched = _matched_key(record, aliases)
        if matched is not None:
            consumed_keys.add(matched)
    # Paired date/time keys are consumed only when they produced detected_at.
    if used_time_pair is not None:
        for time_key in used_time_pair:
            matched = _matched_key(record, (time_key,))
            if matched is not None:
                consumed_keys.add(matched)

    notes = dict(confidence_notes)
    if frp_note:
        notes[frp_note] = True
    if brightness_note:
        notes[brightness_note] = True
    if id_generated:
        notes["id_generated"] = True

    extra_fields = _extra_fields(record, consumed_keys)
    extra_fields.update(sorted(notes.items()))

    return NormalizedHotspot(
        id=str(hotspot_id),
        latitude=latitude,
        longitude=longitude,
        detected_at=detected_at,
        brightness=brightness,
        frp=frp,
        confidence=confidence,
        source=source,
        satellite=satellite,
        instrument=instrument,
        provider=provider,
        extra_fields=extra_fields,
    )


def normalize_records(
    records: list,
    metadata: Optional[dict] = None,
) -> tuple[list[NormalizedHotspot], list[dict]]:
    """Normalize a batch of raw records.

    Returns ``(normalized, dropped)`` where each dropped entry is::

        {"index": int, "record": dict, "reason": str}

    ``reason`` is one of ``"not_a_record"`` or ``"invalid_coordinates"``.
    Order of ``normalized`` follows input order; fully deterministic.
    """
    normalized: list[NormalizedHotspot] = []
    dropped: list[dict] = []

    if records is None:
        return normalized, dropped

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            dropped.append({"index": index, "record": record, "reason": "not_a_record"})
            continue
        hotspot = normalize_record(record, metadata=metadata)
        if hotspot is None:
            dropped.append({"index": index, "record": record, "reason": "invalid_coordinates"})
            continue
        normalized.append(hotspot)

    return normalized, dropped