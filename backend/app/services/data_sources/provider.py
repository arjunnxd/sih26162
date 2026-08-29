"""Provider adapter contract for thermal hotspot data sources.

All future data sources (NASA FIRMS, other satellite feeds, CSV files, JSON
feeds) implement the :class:`Provider` interface. A provider is responsible
only for *fetching raw records in its native shape*; the shared normalizer
converts those records into the common :class:`NormalizedHotspot` format.

Pipeline per provider::

    Provider.fetch_raw()          -> list[dict]   (raw provider records)
                      |
                      v
    normalize_records(...)  -> (list[NormalizedHotspot], dropped)
                      |
                      v
    analysis pipeline later (NOT wired here)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from app.services.data_sources.models import NormalizedHotspot
from app.services.data_sources.normalizer import normalize_records as _normalize_records


class ProviderError(Exception):
    """Raised for provider-level failures (unknown provider, bad config)."""


class Provider(ABC):
    """Abstract contract every thermal data source adapter must satisfy.

    Subclasses must:

    * Set a unique ``name`` (registry key) and optional ``metadata`` describing
      the source (source/satellite/instrument/provider strings).
    * Implement :meth:`fetch_raw` returning a ``list[dict]`` of raw records in
      the provider's own field nomenclature.

    Concrete helpers::

        fetch_hotspots() -> list[NormalizedHotspot]
            Fetches raw records and normalizes them via the shared normalizer.

        fetch_hotspots_with_dropped() -> (list[NormalizedHotspot], list[dict])
            Same, but also returns records that failed normalization (e.g.
            invalid coordinates), each tagged with a reason.
    """

    name: str = "base"
    description: str = "Abstract thermal data source"
    metadata: dict = {}  # optional {"source", "satellite", "instrument", "provider"}

    @abstractmethod
    def fetch_raw(self, **kwargs: Any) -> list[dict]:
        """Return raw hotspot records in this provider's native format."""
        raise NotImplementedError

    def fetch_hotspots(self, **kwargs: Any) -> list[NormalizedHotspot]:
        """Return normalized hotspots (invalid records silently skipped)."""
        normalized, _dropped = _normalize_records(
            self.fetch_raw(**kwargs), metadata=self.metadata
        )
        return normalized

    def fetch_hotspots_with_dropped(
        self, **kwargs: Any
    ) -> tuple[list[NormalizedHotspot], list[dict]]:
        """Return ``(normalized, dropped)`` where ``dropped`` items are dicts
        with ``{"index", "record", "reason"}``."""
        return _normalize_records(self.fetch_raw(**kwargs), metadata=self.metadata)


# Backwards-friendly alias so callers needing the function can import it from
# this module as well (the canonical definition lives in normalizer.py).
normalize_records = _normalize_records