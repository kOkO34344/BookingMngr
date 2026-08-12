"""OTA / channel integrations. Keep all channel-specific logic in this package."""

from app.services.ota.base import (
    ChannelAdapter,
    NormalizedReservation,
    available_sources,
    get_adapter,
    register_adapter,
)

__all__ = [
    "ChannelAdapter",
    "NormalizedReservation",
    "available_sources",
    "get_adapter",
    "register_adapter",
]
