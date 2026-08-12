"""Optional payout ledger.

The MVP keeps payout data on `Reservation` (net_payout_amount, payment_method,
payout_date) and reports read from there. This table exists so that splitting a
reservation across several payouts later is additive: backfill rows from the
reservation columns and point the report service at `PayoutService`.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base, TimestampMixin
from app.models.enums import PayoutSource
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.reservation import Reservation


class Payout(Base, TimestampMixin):
    __tablename__ = "payouts"

    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_id: Mapped[int] = mapped_column(
        ForeignKey("reservations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source: Mapped[PayoutSource] = mapped_column(enum_column(PayoutSource), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(3), default=settings.default_currency, nullable=False
    )
    payout_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    reservation: Mapped["Reservation"] = relationship(back_populates="payouts")
