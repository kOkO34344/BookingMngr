"""Booking.com channel adapter — placeholder.

Planned MVP path: iCal export per room, plus reservation-confirmation email
parsing for the commission/net figures.
"""

from __future__ import annotations

from datetime import date

from app.models.enums import ReservationSource
from app.services.ota.base import NormalizedReservation


class BookingComAdapter:
    source = ReservationSource.BOOKING

    def __init__(self, ical_url: str | None = None, hotel_id: str | None = None) -> None:
        self.ical_url = ical_url
        self.hotel_id = hotel_id

    def fetch_reservations(
        self, *, property_id: int, since: date | None = None
    ) -> list[NormalizedReservation]:
        raise NotImplementedError(
            "Booking.com import is not implemented yet. Create reservations manually "
            "with source='booking', or implement iCal parsing here."
        )
