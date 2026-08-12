from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    literal_column,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base, TimestampMixin
from app.models.enums import (
    BLOCKING_RESERVATION_STATUSES,
    PaymentMethod,
    PaymentStatus,
    ReservationSource,
    ReservationStatus,
)
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.guest import Guest
    from app.models.payout import Payout
    from app.models.property import Property
    from app.models.task import Task
    from app.models.unit import Unit


#: SQL predicate limiting the overlap constraint to statuses that hold a unit.
#: Derived from the enum so the two cannot drift — but note that changing the
#: set requires a new migration to rebuild the constraint, since existing DDL
#: is frozen at the version that created it.
BLOCKING_STATUS_SQL = "status IN ({})".format(
    ", ".join(f"'{status.value}'" for status in sorted(BLOCKING_RESERVATION_STATUSES))
)

#: Half-open day range: the check-out day is free for the next guest.
STAY_RANGE_SQL = "daterange(check_in_date, check_out_date, '[)')"


class Reservation(Base, TimestampMixin):
    """Unified booking record for every channel (OTA, phone, WhatsApp, email)."""

    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("check_out_date > check_in_date", name="ck_reservation_date_order"),
        Index("ix_reservations_unit_dates", "unit_id", "check_in_date", "check_out_date"),
        Index("ix_reservations_property_dates", "property_id", "check_in_date", "check_out_date"),
        # The service layer rejects double bookings before writing, but that is
        # a check-then-act race: two concurrent requests can both pass it. This
        # makes the database the authority. Postgres-only (it needs btree_gist
        # and range types), so SQLite tests fall back to the service check.
        ExcludeConstraint(
            (literal_column("unit_id"), "="),
            (literal_column(STAY_RANGE_SQL), "&&"),
            name="ex_reservations_no_overlap",
            where=literal_column(BLOCKING_STATUS_SQL),
        ).ddl_if(dialect="postgresql"),
    )

    # --- Identity ----------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), index=True, nullable=False
    )
    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    guest_id: Mapped[int | None] = mapped_column(
        ForeignKey("guests.id", ondelete="SET NULL"), index=True, nullable=True
    )
    # Denormalised so a booking can be taken by phone without creating a Guest.
    guest_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # --- Dates -------------------------------------------------------------
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    check_out_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    number_of_guests: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # --- Source / channel --------------------------------------------------
    source: Mapped[ReservationSource] = mapped_column(
        enum_column(ReservationSource), nullable=False, index=True
    )
    #: OTA confirmation code, or a free-text note for phone/WhatsApp/email.
    source_reference: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)

    # --- Status ------------------------------------------------------------
    status: Mapped[ReservationStatus] = mapped_column(
        enum_column(ReservationStatus),
        default=ReservationStatus.CONFIRMED,
        nullable=False,
        index=True,
    )

    # --- Finance -----------------------------------------------------------
    #: Total the guest paid, including platform fees.
    gross_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    #: OTA / platform commission and service fees.
    fees_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    #: Money that actually reaches the owner. Basis for all revenue reports.
    net_payout_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    currency: Mapped[str] = mapped_column(
        String(3), default=settings.default_currency, nullable=False
    )
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        enum_column(PaymentMethod), nullable=True
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        enum_column(PaymentStatus), default=PaymentStatus.PENDING, nullable=False
    )
    #: MVP shortcut — kept here until the Payout table is introduced.
    payout_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # --- Metadata ----------------------------------------------------------
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Raw payload from an iCal/email importer, for later reconciliation.
    external_payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    property: Mapped["Property"] = relationship(back_populates="reservations")
    unit: Mapped["Unit"] = relationship(back_populates="reservations")
    guest: Mapped["Guest | None"] = relationship(back_populates="reservations")
    tasks: Mapped[list["Task"]] = relationship(back_populates="reservation")
    payouts: Mapped[list["Payout"]] = relationship(
        back_populates="reservation", cascade="all, delete-orphan"
    )

    # NOTE: `property` is taken by the relationship above, so the builtin
    # decorator is unavailable inside this class body — hybrid_property both
    # works around that and stays usable in queries.
    @hybrid_property
    def nights(self) -> int:
        return (self.check_out_date - self.check_in_date).days

    @hybrid_property
    def display_guest_name(self) -> str:
        if self.guest is not None:
            return self.guest.full_name
        return self.guest_name or "Guest"
