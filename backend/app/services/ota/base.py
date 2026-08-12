"""Channel-integration seam.

No OTA API is implemented yet. What exists is the boundary: routers never talk
to Airbnb/Booking directly, they go through a `ChannelAdapter`. Adding a real
integration later means implementing this protocol and registering it — no
changes to endpoints or models.

Expected first implementations:
  * iCal pull (Airbnb & Booking both expose per-listing iCal feeds)
  * Email/inbox parsing for confirmations
  * Official partner APIs, once the account qualifies
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol, runtime_checkable

from app.models.enums import ReservationSource


@dataclass(slots=True)
class NormalizedReservation:
    """Channel-agnostic booking payload produced by an adapter."""

    source: ReservationSource
    source_reference: str
    check_in_date: date
    check_out_date: date
    guest_name: str | None = None
    guest_email: str | None = None
    guest_phone: str | None = None
    number_of_guests: int = 1
    gross_amount: Decimal = Decimal("0")
    fees_amount: Decimal = Decimal("0")
    net_payout_amount: Decimal | None = None
    currency: str | None = None
    unit_external_id: str | None = None
    is_canceled: bool = False
    raw: dict = field(default_factory=dict)


@runtime_checkable
class ChannelAdapter(Protocol):
    source: ReservationSource

    def fetch_reservations(
        self, *, property_id: int, since: date | None = None
    ) -> list[NormalizedReservation]:
        """Pull bookings from the channel and normalize them."""
        ...


_REGISTRY: dict[ReservationSource, ChannelAdapter] = {}


def register_adapter(adapter: ChannelAdapter) -> None:
    _REGISTRY[adapter.source] = adapter


def get_adapter(source: ReservationSource) -> ChannelAdapter | None:
    return _REGISTRY.get(source)


def available_sources() -> list[ReservationSource]:
    return list(_REGISTRY)
