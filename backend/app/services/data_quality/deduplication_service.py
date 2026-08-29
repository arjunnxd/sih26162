"""Deterministic hotspot deduplication for the thermal intelligence platform.

Strategy
--------
Records are compared pairwise against kept representatives. A comparison
produces an explainable similarity score built from independent signals:

    spatial   - great-circle distance (Haversine, reused from
                ``app.services.geospatial_service.calculate_distance_m``)
                is within ``coordinate_tolerance_m``.
    temporal  - absolute difference of detection timestamps is within
                ``timestamp_tolerance_seconds``.
    source    - both records carry a known source/provider and they are equal.

Each satisfied signal adds its configured weight (default: spatial 40,
temporal 30, source 15; max 85). Weights intentionally stay below 100 so a
single missing signal can never silently produce a full match.

Categories
----------
    EXACT_DUPLICATE  identical non-empty id, OR identical coordinates AND
                     identical detection timestamp (both fully known).
    LIKELY_DUPLICATE similarity score >= ``likely_duplicate_threshold``.
    UNIQUE           neither condition holds.

Ties between signals are resolved by evaluation order (spatial, temporal,
source), never by chance.

RESOLUTION
----------
When a duplicate is found, a deterministic keeper is chosen with
:func:`choose_keeper` (higher quality score, then more complete record, then
higher numeric confidence, then more recent timestamp, then a stable
string-encoding tie-breaker). Input order never affects the outcome.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.services.data_quality.models import (
    DUPLICATE_EXACT,
    DUPLICATE_LIKELY,
    DUPLICATE_UNIQUE,
    DeduplicationConfig,
)
from app.services.data_quality.quality_service import (
    finite_float,
    parse_timestamp_epoch,
)
from app.services.geospatial_service import calculate_distance_m

#: Canonical (record_id, latitude, longitude, epoch, source) extraction helper.
_FIELDS = ("id", "latitude", "longitude", "detected_at", "source", "provider")


def _extract(record: Any) -> Dict[str, Any]:
    """Return canonical comparison fields from any supported record form."""
    record = record if isinstance(record, dict) else {}
    record_id = record.get("id")
    source = record.get("source") or record.get("provider")
    return {
        "id": str(record_id).strip() if record_id is not None and str(record_id).strip() else None,
        "lat": finite_float(record.get("latitude")),
        "lon": finite_float(record.get("longitude")),
        "epoch": parse_timestamp_epoch(record.get("detected_at")),
        "source": str(source).strip() if source else None,
    }


def compare_records(
    record_a: Any,
    record_b: Any,
    config: Optional[DeduplicationConfig] = None,
) -> Tuple[str, float, List[str]]:
    """Compare two records and return ``(category, score, reasons)``.

    Deterministic: identical inputs always yield identical outputs.
    """
    config = config or DeduplicationConfig()
    a = _extract(record_a)
    b = _extract(record_b)

    # --- Exact duplicate: same id ------------------------------------------------
    if a["id"] is not None and a["id"] == b["id"]:
        return DUPLICATE_EXACT, 100.0, ["Records share the same identifier"]

    # --- Exact duplicate: identical coordinates AND timestamp (both known) -------
    coords_known = a["lat"] is not None and a["lon"] is not None and b["lat"] is not None and b["lon"] is not None
    times_known = a["epoch"] is not None and b["epoch"] is not None
    if (
        coords_known
        and times_known
        and a["lat"] == b["lat"]
        and a["lon"] == b["lon"]
        and a["epoch"] == b["epoch"]
    ):
        return (
            DUPLICATE_EXACT,
            100.0,
            ["Records share identical coordinates and detection timestamp"],
        )

    # --- Similarity scoring ---------------------------------------------------------
    score = 0.0
    reasons: List[str] = []

    if coords_known:
        distance = calculate_distance_m(a["lat"], a["lon"], b["lat"], b["lon"])
        if distance is not None and distance <= config.coordinate_tolerance_m:
            score += config.spatial_score_weight
            reasons.append(
                f"Coordinates are {round(distance, 1)} m apart "
                f"(within {int(config.coordinate_tolerance_m)} m tolerance)"
            )

    if times_known:
        delta = abs(a["epoch"] - b["epoch"])
        if delta <= config.timestamp_tolerance_seconds:
            score += config.temporal_score_weight
            reasons.append(
                f"Detection timestamps differ by {int(round(delta))} s "
                f"(within {int(config.timestamp_tolerance_seconds)} s tolerance)"
            )

    if a["source"] is not None and a["source"] == b["source"]:
        score += config.source_score_weight
        reasons.append(f"Records come from the same source ({a['source']})")

    if score >= config.likely_duplicate_threshold:
        return DUPLICATE_LIKELY, round(score, 2), reasons
    return DUPLICATE_UNIQUE, round(score, 2), reasons


def choose_keeper(
    record_a: Any,
    record_b: Any,
    quality_a: float,
    quality_b: float,
    completeness_a: float,
    completeness_b: float,
) -> Tuple[bool, List[str]]:
    """Deterministically decide whether ``record_a`` should be kept over ``record_b``.

    Resolution priority (first difference wins; documented, never random):
        1. Higher quality score
        2. More complete record (completeness ratio)
        3. Higher numeric confidence (missing confidence loses to a number)
        4. More recent detection timestamp (missing timestamp loses)
        5. Stable deterministic tie-breaker on the full encoded record

    Returns ``(keep_a, reasons)`` where ``reasons`` explains the decision.
    """
    reasons: List[str] = []
    dict_a = record_a if isinstance(record_a, dict) else {}
    dict_b = record_b if isinstance(record_b, dict) else {}

    if quality_a != quality_b:
        winner = quality_a > quality_b
        reasons.append(f"Quality score comparison ({quality_a} vs {quality_b})")
        return winner, reasons

    if completeness_a != completeness_b:
        winner = completeness_a > completeness_b
        reasons.append(f"Completeness comparison ({completeness_a} vs {completeness_b})")
        return winner, reasons

    conf_a = finite_float(dict_a.get("confidence"))
    conf_b = finite_float(dict_b.get("confidence"))
    if conf_a != conf_b:
        winner = (conf_a is not None) and (conf_b is None or conf_a > conf_b)
        reasons.append(f"Detection confidence comparison ({conf_a} vs {conf_b})")
        return winner, reasons

    epoch_a = parse_timestamp_epoch(dict_a.get("detected_at"))
    epoch_b = parse_timestamp_epoch(dict_b.get("detected_at"))
    if epoch_a != epoch_b:
        winner = (epoch_a is not None) and (epoch_b is None or epoch_a > epoch_b)
        reasons.append("Detection timestamp recency comparison")
        return winner, reasons

    # Final stable tie-breaker on the full encoded record content.
    enc_a = repr(sorted(dict_a.items(), key=lambda kv: kv[0]))
    enc_b = repr(sorted(dict_b.items(), key=lambda kv: kv[0]))
    reasons.append("Records are equivalent; stable encoding tie-breaker applied")
    return enc_a >= enc_b, reasons


def deduplicate_records(
    records: List[Any],
    qualities: List[Any],
    config: Optional[DeduplicationConfig] = None,
) -> Tuple[List[Any], List[Any]]:
    """Partition records into ``(kept, duplicate_matches)`` deterministically.

    ``qualities`` must align with ``records`` and contain ``QualityAssessment``
    objects. Each record is compared against kept representatives in input
    order; on a match, :func:`choose_keeper` deterministically decides whether
    the new record replaces the kept representative or becomes the duplicate.
    The loser is reported as a ``DuplicateMatch`` pointing at the winner's id.
    """
    from app.services.data_quality.models import DuplicateMatch

    config = config or DeduplicationConfig()
    kept: List[Any] = []
    kept_quality: List[Any] = []
    duplicates: List[DuplicateMatch] = []

    for record, quality in zip(records, qualities):
        matched = False

        for kept_index, candidate in enumerate(kept):
            category, score, reasons = compare_records(record, candidate, config)
            if category == DUPLICATE_UNIQUE:
                continue

            keep_new, decision = choose_keeper(
                record,
                candidate,
                quality.quality_score,
                kept_quality[kept_index].quality_score,
                quality.completeness_ratio,
                kept_quality[kept_index].completeness_ratio,
            )
            winner, loser, loser_quality = (
                (record, candidate, kept_quality[kept_index])
                if keep_new
                else (candidate, record, quality)
            )
            duplicates.append(
                DuplicateMatch(
                    record=loser,
                    category=category,
                    similarity_score=score,
                    reasons=list(reasons) + list(decision),
                    duplicate_of=_extract(winner)["id"],
                )
            )
            if keep_new:
                kept[kept_index] = record
                kept_quality[kept_index] = quality
            matched = True
            break

        if not matched:
            kept.append(record)
            kept_quality.append(quality)

    return kept, duplicates
