"""High-level thermal data quality and deduplication processor.

Pipeline (isolated; Member 1 will integrate later):

    INPUT RECORDS  ->  QUALITY ANALYSIS  ->  INVALID RECORD HANDLING
        ->  DUPLICATE DETECTION  ->  DUPLICATE RESOLUTION
        ->  CLEAN UNIQUE RECORDS  ->  QUALITY REPORT

Usage:
    from app.services.data_quality import process_hotspots

    result = process_hotspots(records)          # ProcessingResult
    result.to_dict()                            # JSON-friendly structure

INPUT COMPATIBILITY
-------------------
``process_hotspots`` safely accepts, per record:
    * :class:`~app.services.data_sources.models.NormalizedHotspot` objects
      (via ``to_dict()``),
    * dicts produced by ``NormalizedHotspot.to_dict()``,
    * dicts produced by ``NormalizedHotspot.to_pipeline_dict()``,
    * plain provider dicts using the canonical field names,
    * ``None`` / non-dict garbage (rejected with an explanation, never a crash).

The original input objects are always preserved in the output; canonicalized
copies are used only for internal analysis. The existing data_sources
normalizer is NOT modified or re-used for mutation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.services.data_quality.deduplication_service import deduplicate_records
from app.services.data_quality.models import (
    ProcessingResult,
    QualityConfig,
)
from app.services.data_quality.quality_service import assess_quality

try:  # pragma: no cover - trivial import guard, targeted (not bare except)
    from app.services.data_sources.models import NormalizedHotspot
except ImportError:  # pragma: no cover - package used standalone
    NormalizedHotspot = None


def _canonicalize(record: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Convert any supported input into a canonical dict.

    Returns ``(canonical_dict, None)`` on success or ``(None, reason)`` when
    the record cannot be processed at all. Never raises for bad input.
    """
    if record is None:
        return None, "Record is None"
    if NormalizedHotspot is not None and isinstance(record, NormalizedHotspot):
        return dict(record.to_dict()), None
    if isinstance(record, dict):
        return dict(record), None
    if hasattr(record, "to_dict") and callable(record.to_dict):
        # Any duck-typed hotspot object exposing to_dict().
        converted = record.to_dict()
        if isinstance(converted, dict):
            return dict(converted), None
        return None, "to_dict() did not produce a dictionary"
    return None, f"Unsupported record type: {type(record).__name__}"


def process_hotspots(
    records: Any,
    quality_config: Optional[QualityConfig] = None,
    dedup_config: Any = None,
) -> ProcessingResult:
    """Run quality analysis, invalid-record handling, and deduplication.

    Args:
        records: iterable of supported record forms (see module docstring).
        quality_config: optional :class:`QualityConfig` override.
        dedup_config: optional :class:`DeduplicationConfig` override.

    Returns:
        :class:`ProcessingResult` with ``accepted``, ``duplicates``,
        ``rejected``, and ``summary``. Deterministic: the same input always
        produces the same output.
    """
    from app.services.data_quality.models import DeduplicationConfig

    quality_config = quality_config or QualityConfig()
    dedup_config = dedup_config or DeduplicationConfig()

    canonical: List[Dict[str, Any]] = []
    originals: List[Any] = []
    rejected: List[Dict[str, Any]] = []

    if records is None:
        records = []
    try:
        iterator = iter(records)
    except TypeError:
        # A single non-iterable object is treated as one malformed record.
        iterator = iter([records])

    for record in iterator:
        converted, reason = _canonicalize(record)
        if converted is None:
            rejected.append({"record": record, "reason": reason, "quality": None})
            continue
        canonical.append(converted)
        originals.append(record)

    if not canonical:
        return ProcessingResult(
            accepted=[],
            duplicates=[],
            rejected=rejected,
            summary=_summary([], [], rejected),
        )

    # -- Quality analysis ---------------------------------------------------
    qualities = [assess_quality(record, quality_config) for record in canonical]

    # -- Invalid record handling ----------------------------------------------
    valid_pairs: List[Tuple[Any, Any, Dict[str, Any]]] = []
    for original, canonical_record, quality in zip(originals, canonical, qualities):
        if quality.is_valid and quality.quality_level != "INVALID":
            valid_pairs.append((original, canonical_record, quality))
        else:
            rejected.append(
                {
                    "record": original,
                    "reason": "Record is invalid: coordinates are missing or invalid",
                    "quality": quality.to_dict(),
                }
            )

    # -- Duplicate detection + resolution ---------------------------------------
    kept_canonical, duplicate_matches = deduplicate_records(
        [pair[1] for pair in valid_pairs],
        [pair[2] for pair in valid_pairs],
        dedup_config,
    )

    # Map kept canonical records back to their original input objects.
    accepted: List[Any] = []
    for kept in kept_canonical:
        for original, canonical_record in ((p[0], p[1]) for p in valid_pairs):
            if canonical_record is kept or canonical_record == kept:
                accepted.append(original)
                break

    # Report duplicates against the ORIGINAL input objects, with the loser's
    # quality assessment attached for explainability.
    duplicate_matches = _map_to_originals(duplicate_matches, valid_pairs)
    for match in duplicate_matches:
        for original, canonical_record, quality in valid_pairs:
            if match.record is original:
                match.quality = quality.to_dict()  # type: ignore[attr-defined]
                break

    return ProcessingResult(
        accepted=accepted,
        duplicates=duplicate_matches,
        rejected=rejected,
        summary=_summary(accepted, duplicate_matches, rejected, qualities),
    )


def _map_to_originals(
    duplicate_matches: List[Any],
    pairs: List[Tuple[Any, Any, Any]],
) -> List[Any]:
    """Replace canonical records inside duplicate matches with the originals."""
    for match in duplicate_matches:
        for original, canonical_record, _ in pairs:
            if match.record is canonical_record or match.record == canonical_record:
                match.record = original
                break
    return duplicate_matches


def _summary(
    accepted: List[Any],
    duplicates: List[Any],
    rejected: List[Dict[str, Any]],
    qualities: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """Build the aggregate quality report (counts + level distribution)."""
    summary: Dict[str, Any] = {
        "total_input": len(accepted) + len(duplicates) + len(rejected),
        "accepted_count": len(accepted),
        "duplicate_count": len(duplicates),
        "rejected_count": len(rejected),
        "quality_levels": {},
        "average_quality_score": None,
    }

    level_counts: Dict[str, int] = {}
    scores: List[float] = []
    for match in duplicates:
        quality = getattr(match, "quality", None)
        level = quality.get("quality_level") if isinstance(quality, dict) else None
        if level:
            level_counts[level] = level_counts.get(level, 0) + 1
    if qualities:
        for quality in qualities:
            level_counts[quality.quality_level] = level_counts.get(quality.quality_level, 0) + 1
            scores.append(quality.quality_score)

    summary["quality_levels"] = level_counts
    if scores:
        summary["average_quality_score"] = round(sum(scores) / len(scores), 2)
    return summary
