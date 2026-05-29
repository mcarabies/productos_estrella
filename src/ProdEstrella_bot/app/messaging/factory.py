"""
WhatsApp Provider Factory — Strategy Pattern.
Reads WHATSAPP_PROVIDER from settings and returns the correct adapter.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import WhatsAppProvider, settings
from app.messaging.protocols import WhatsAppProviderProtocol


@lru_cache(maxsize=1)
def get_whatsapp_provider() -> WhatsAppProviderProtocol:
    """
    Return the active WhatsApp adapter as selected by settings.WHATSAPP_PROVIDER.

    Cached: adapter is instantiated once per process (singleton behaviour).
    The business layer never needs to know which provider is active.
    """
    provider = settings.whatsapp_provider

    if provider == WhatsAppProvider.evolution:
        from app.messaging.providers.evolution.adapter import EvolutionAdapter
        return EvolutionAdapter()

    if provider == WhatsAppProvider.meta:
        from app.messaging.providers.meta.adapter import MetaAdapter
        return MetaAdapter()

    raise ValueError(
        f"Unknown WHATSAPP_PROVIDER '{provider}'. "
        "Valid values: 'evolution', 'meta'."
    )
