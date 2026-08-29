"""Thermal Data Source Adapter Foundation.

Isolated ingestion architecture for normalizing thermal hotspot data from
future external providers into one common internal format.

Visual layout::

    External Data Source
            |
            v
    Provider Adapter  (provider.Provider.fetch_raw)
            |
            v
    Raw Provider Response (list[dict] in provider's own field names)
            |
            v
    Validation + Normalization (normalizer.normalize_records)
            |
            v
    Common Hotspot Format (models.NormalizedHotspot)
            |
            v
    Ready for Analysis Pipeline (NormalizedHotspot.to_pipeline_dict)

Public API (import from here)::

    NormalizedHotspot,
    Provider, ProviderError,
    normalize_record, normalize_records,
    build_provider, get_provider, available_providers, register_provider
"""

from __future__ import annotations

from app.services.data_sources.models import NormalizedHotspot
from app.services.data_sources.normalizer import normalize_record, normalize_records
from app.services.data_sources.provider import Provider, ProviderError
from app.services.data_sources.providers import (
    available_providers,
    build_provider,
    get_provider,
    register_provider,
)

__all__ = [
    "NormalizedHotspot",
    "Provider",
    "ProviderError",
    "normalize_record",
    "normalize_records",
    "build_provider",
    "get_provider",
    "available_providers",
    "register_provider",
]