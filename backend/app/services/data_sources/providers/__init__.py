"""Provider registry for thermal hotspot data sources.

Future providers register here (or decorator-register via ``register_provider``)
so callers can build adapters by name without importing provider classes
directly. Kept deterministic - registration order is insertion order but
:func:`available_providers` returns a sorted list.
"""

from __future__ import annotations

from typing import Any, Optional
from app.services.data_sources.providers.firms_provider import FIRMSProvider
from app.services.data_sources.provider import Provider, ProviderError
from app.services.data_sources.providers.mock_provider import MockFirmsProvider

_REGISTRY: dict[str, type[Provider]] = {}


def register_provider(provider_cls: type[Provider]) -> type[Provider]:
    """Register a Provider subclass by its ``name`` (idempotent override)."""
    if not issubclass(provider_cls, Provider):
        raise ProviderError(f"{provider_cls!r} must be a subclass of Provider")
    _REGISTRY[provider_cls.name] = provider_cls
    return provider_cls


# Seed the registry with the bundled demo provider.
register_provider(MockFirmsProvider)
register_provider(FIRMSProvider)

def get_provider(name: str) -> type[Provider]:
    """Return the provider class registered under ``name``."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise ProviderError(
            f"Unknown provider '{name}'. Available: {available_providers()}"
        ) from None


def build_provider(name: str, **kwargs: Any) -> Provider:
    """Instantiate the provider registered under ``name``."""
    return get_provider(name)(**kwargs)


def available_providers() -> list[str]:
    """Return sorted names of all registered providers."""
    return sorted(_REGISTRY)