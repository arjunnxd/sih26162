"""Thermal data quality and deduplication engine (isolated module).

Sits conceptually between NORMALIZED DATA and the ANALYSIS PIPELINE:

    INPUT RECORDS -> QUALITY ANALYSIS -> INVALID RECORD HANDLING
        -> DUPLICATE DETECTION -> DUPLICATE RESOLUTION
        -> CLEAN UNIQUE RECORDS -> QUALITY REPORT

Public API:
    process_hotspots(records, quality_config=None, dedup_config=None)
        -> ProcessingResult(accepted, duplicates, rejected, summary)
    assess_quality(record) / assess_quality_batch(records)
    compare_records(a, b) / deduplicate_records(records, qualities)
    choose_keeper(...)   - documented deterministic resolution strategy
    QualityConfig / DeduplicationConfig   - all thresholds configurable

Deterministic, explainable, stdlib-only. No FastAPI, no Pydantic, no network.
NOT yet wired into the analysis pipeline or API - integration is owned by
Member 1. Accepts NormalizedHotspot objects, ``to_dict()`` dicts, and
``to_pipeline_dict()`` dicts.
"""

from app.services.data_quality.deduplication_service import (
    choose_keeper,
    compare_records,
    deduplicate_records,
)
from app.services.data_quality.models import (
    DUPLICATE_EXACT,
    DUPLICATE_LIKELY,
    DUPLICATE_UNIQUE,
    QUALITY_EXCELLENT,
    QUALITY_GOOD,
    QUALITY_INVALID,
    QUALITY_MODERATE,
    QUALITY_POOR,
    DeduplicationConfig,
    DuplicateMatch,
    ProcessingResult,
    QualityAssessment,
    QualityConfig,
)
from app.services.data_quality.processor import process_hotspots
from app.services.data_quality.quality_service import (
    assess_quality,
    assess_quality_batch,
    finite_float,
    parse_timestamp_epoch,
)

__all__ = [
    # high-level API
    "process_hotspots",
    # quality engine
    "assess_quality",
    "assess_quality_batch",
    "finite_float",
    "parse_timestamp_epoch",
    "QualityAssessment",
    "QualityConfig",
    # deduplication engine
    "compare_records",
    "deduplicate_records",
    "choose_keeper",
    "DeduplicationConfig",
    "DuplicateMatch",
    # result container
    "ProcessingResult",
    # level constants
    "QUALITY_EXCELLENT",
    "QUALITY_GOOD",
    "QUALITY_MODERATE",
    "QUALITY_POOR",
    "QUALITY_INVALID",
    # duplicate constants
    "DUPLICATE_EXACT",
    "DUPLICATE_LIKELY",
    "DUPLICATE_UNIQUE",
]
