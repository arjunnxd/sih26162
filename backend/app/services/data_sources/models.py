"""Common normalized thermal hotspot representation.

This module defines the single normalized shape that every provider adapter
produces, independent of the raw nomenclature of any external data source.
It is a plain ``dataclass`` - no FastAPI, no Pydantic - so it is trivially
testable and serializable.

The seven core fields match the contract consumed by the existing analysis
pipeline (``hotspot_analysis_service.analyze_hotspot``):

    id, latitude, longitude, detected_at, brightness, frp, confidence

Optional metadata (source, satellite, instrument, provider) is preserved so
providers can be audited later. Unknown provider-specific fields are kept in
``extra_fields`` so no information is silently discarded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

#: Core fields recognized by the existing analysis pipeline.
CORE_FIELDS = (
    "id",
    "latitude",
    "longitude",
    "detected_at",
    "brightness",
    "frp",
    "confidence",
)


@dataclass
class NormalizedHotspot:
    """A single thermal hotspot in the common internal format.

    Attributes:
        id: Stable identifier. When the source does not provide one, the
            normalizer generates a deterministic placeholder.
        latitude: Decimal degrees, validated by the normalizer ([-90, 90]).
        longitude: Decimal degrees, validated by the normalizer ([-180, 180]).
        detected_at: Normalized ISO-8601 UTC string (``YYYY-MM-DDTHH:MM:SSZ``),
            or ``None`` when the source timestamp could not be parsed.
        brightness: Thermal brightness in Kelvin-equivalent units, or ``None``.
        frp: Fire Radiative Power in MW, or ``None``.
        confidence: Detection confidence normalized to the 0..1 range, or
            ``None`` when the source value is non-numeric (the raw label is
            preserved in ``extra_fields``).
        source: Name of the upstream data source, when known.
        satellite: Platform name, when known.
        instrument: Sensor name, when known.
        provider: Adapter/provider identifier, when known.
        extra_fields: Dict of source fields that do not map to any canonical
            field plus transparent normalization notes (e.g. textual
            confidence preserved as ``confidence_label``).
    """

    id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    detected_at: Optional[str] = None
    brightness: Optional[float] = None
    frp: Optional[float] = None
    confidence: Optional[float] = None

    source: Optional[str] = None
    satellite: Optional[str] = None
    instrument: Optional[str] = None
    provider: Optional[str] = None

    extra_fields: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Return a plain, JSON-serializable dict of every field."""
        return {
            "id": self.id,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "detected_at": self.detected_at,
            "brightness": self.brightness,
            "frp": self.frp,
            "confidence": self.confidence,
            "source": self.source,
            "satellite": self.satellite,
            "instrument": self.instrument,
            "provider": self.provider,
            "extra_fields": dict(self.extra_fields),
        }

    def to_pipeline_dict(self) -> dict:
        """Return a dict with exactly the core fields the analysis pipeline
        consumes (``analyze_hotspot``). Safe for future integration.
        """
        return {name: getattr(self, name) for name in CORE_FIELDS}

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "NormalizedHotspot":
        """Construct a hotspot from a dict, ignoring unknown keys.

        This is a thin convenience mirror of :func:`to_dict`; the canonical
        route for external data is the normalizer, which validates values.
        """
        data = data or {}
        known = CORE_FIELDS + (
            "source",
            "satellite",
            "instrument",
            "provider",
            "extra_fields",
        )
        kwargs: dict[str, Any] = {}
        for key in known:
            if key in data:
                kwargs[key] = data[key]
        return cls(**kwargs)