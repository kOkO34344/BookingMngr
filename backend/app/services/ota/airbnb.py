"""Airbnb channel adapter — placeholder.

Planned MVP path: parse the per-listing iCal export (no partner API needed).
Payout amounts are not in the iCal feed, so the manager still fills them in, or
a later CSV/statement importer backfills them.
"""

from __future__ import annotations

from datetime import date

from app.models.enums import ReservationSource
from app.services.ota.base import NormalizedReservation


class AirbnbAdapter:
    source = ReservationSource.AIRBNB

    def __init__(self, ical_url: str | None = None) -> None:
        self.ical_url = ical_url

    def fetch_reservations(
        self, *, property_id: int, since: date | None = None
    ) -> list[NormalizedReservation]:
        raise NotImplementedError(
            "Airbnb import is not implemented yet. Create reservations manually "
            "with source='airbnb', or implement iCal parsing here."
        )
