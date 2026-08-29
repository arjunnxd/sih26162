"""Data models and configuration for the thermal data quality engine.

Plain-dataclasses only - no FastAPI, no Pydantic, no I/O. Every threshold is
configurable and every result object is deterministic and JSON-friendly.

QUALITY LEVELS (configurable in :class:`QualityConfig`)
    EXCELLENT  score >= excellent_min (default 90)
    GOOD       score >= good_min      (default 75)
    MODERATE   score >= moderate_min  (default 50)
    POOR       score >= poor_min      (default 1)
    INVALID    score == 0 (record cannot be used - e.g. missing/invalid coords)

DUPLICATE CATEGORIES (:class:`DeduplicationConfig`)
    EXACT_DUPLICATE  identical record id, or identical coordinates AND
                     identical detection timestamp.
    LIKELY_DUPLICATE explainable similarity score >= likely_duplicate_threshold.
    UNIQUE           not a duplicate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Quality levels
# ---------------------------------------------------------------------------
QUALITY_EXCELLENT = "EXCELLENT"
QUALITY_GOOD = "GOOD"
QUALITY_MODERATE = "MODERATE"
QUALITY_POOR = "POOR"
QUALITY_INVALID = "INVALID"

QUALITY_LEVELS = (
    QUALITY_EXCELLENT,
    QUALITY_GOOD,
    QUALITY_MODERATE,
    QUALITY_POOR,
    QUALITY_INVALID,
)

# ---------------------------------------------------------------------------
# Duplicate categories
# ---------------------------------------------------------------------------
DUPLICATE_EXACT = "EXACT_DUPLICATE"
DUPLICATE_LIKELY = "LIKELY_DUPLICATE"
DUPLICATE_UNIQUE = "UNIQUE"


@dataclass
class QualityConfig:
    """Configurable weights and thresholds for quality scoring.

    Weights are contribution points per component and sum to 100. A component
    earns its weight only when its value is present AND valid; missing or
    invalid values contribute 0 (never a fabricated value).
    """

    # Component weights (sum = 100).
    weight_coordinates: float = 30.0   # split evenly: 15 per axis
    weight_timestamp: float = 15.0
    weight_brightness: float = 15.0
    weight_frp: float = 15.0
    weight_confidence: float = 15.0
    weight_id: float = 10.0

    # Level thresholds.
    excellent_min: float = 90.0
    good_min: float = 75.0
    moderate_min: float = 50.0
    poor_min: float = 1.0

    def level_for(self, score: float) -> str:
        """Map a 0-100 quality score to its level (deterministic)."""
        if score >= self.excellent_min:
            return QUALITY_EXCELLENT
        if score >= self.good_min:
            return QUALITY_GOOD
        if score >= self.moderate_min:
            return QUALITY_MODERATE
        if score >= self.poor_min:
            return QUALITY_POOR
        return QUALITY_INVALID



@dataclass
class QualityAssessment:
    """Explainable quality result for a single hotspot record."""

    quality_score: float
    quality_level: str
    quality_reasons: List[str] = field(default_factory=list)
    quality_warnings: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    invalid_fields: List[str] = field(default_factory=list)
    completeness_ratio: float = 0.0
    is_valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain JSON-serializable dict of the assessment."""
        return {
            "quality_score": self.quality_score,
            "quality_level": self.quality_level,
            "quality_reasons": list(self.quality_reasons),
            "quality_warnings": list(self.quality_warnings),
            "missing_fields": list(self.missing_fields),
            "invalid_fields": list(self.invalid_fields),
            "completeness_ratio": self.completeness_ratio,
            "is_valid": self.is_valid,
        }


@dataclass
class DeduplicationConfig:
    """Configurable thresholds for deterministic deduplication.

    Scoring model (documented in ``deduplication_service.compare_records``):
        spatial similarity  + spatial_score_weight  when the great-circle
                            distance between two records is <= coordinate_tolerance_m.
        temporal similarity + temporal_score_weight when the absolute detection
                            timestamp difference is <= timestamp_tolerance_seconds.
        source agreement    + source_score_weight  when both records carry a
                            known, equal source/provider (different or unknown
                            sources contribute 0 - never a penalty).
    """

    coordinate_tolerance_m: float = 100.0
    timestamp_tolerance_seconds: float = 300.0
    likely_duplicate_threshold: float = 70.0
    spatial_score_weight: float = 40.0
    temporal_score_weight: float = 30.0
    source_score_weight: float = 15.0


@dataclass
class DuplicateMatch:
    """A record identified as a duplicate of a kept representative."""

    record: Any                       # original input object (unchanged)
    category: str                     # EXACT_DUPLICATE | LIKELY_DUPLICATE
    similarity_score: float
    reasons: List[str] = field(default_factory=list)
    duplicate_of: Optional[str] = None  # id of the kept record

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain JSON-serializable dict of the match."""
        return {
            "record": self.record,
            "category": self.category,
            "similarity_score": self.similarity_score,
            "reasons": list(self.reasons),
            "duplicate_of": self.duplicate_of,
        }


@dataclass
class ProcessingResult:
    """Structured output of :func:`processor.process_hotspots`.

    accepted   - original input records that are valid and unique (input order).
    duplicates - :class:`DuplicateMatch` entries removed during deduplication.
    rejected   - dicts: {"record", "reason", "quality"} for unusable records.
    summary    - aggregate counts and quality distribution.
    """

    accepted: List[Any] = field(default_factory=list)
    duplicates: List[DuplicateMatch] = field(default_factory=list)
    rejected: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain JSON-serializable dict of the result."""
        return {
            "accepted": list(self.accepted),
            "duplicates": [d.to_dict() for d in self.duplicates],
            "rejected": [dict(r) for r in self.rejected],
            "summary": dict(self.summary),
        }
