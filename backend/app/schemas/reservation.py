from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, computed_field, model_validator

from app.core.config import settings
from app.models.enums import (
    PaymentMethod,
    PaymentStatus,
    ReservationSource,
    ReservationStatus,
)
from app.schemas.common import ORMModel


class ReservationBase(BaseModel):
    property_id: int
    unit_id: int
    guest_id: int | None = None
    guest_name: str | None = Field(default=None, max_length=200)

    check_in_date: date
    check_out_date: date
    number_of_guests: int = Field(default=1, ge=1, le=50)

    source: ReservationSource
    source_reference: str | None = Field(default=None, max_length=200)

    status: ReservationStatus = ReservationStatus.CONFIRMED

    gross_amount: Decimal = Field(default=Decimal("0"), ge=0)
    fees_amount: Decimal = Field(default=Decimal("0"), ge=0)
    net_payout_amount: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default=settings.default_currency, min_length=3, max_length=3)
    payment_method: PaymentMethod | None = None
    payment_status: PaymentStatus = PaymentStatus.PENDING
    payout_date: date | None = None

    notes: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> "ReservationBase":
        if self.check_out_date <= self.check_in_date:
            raise ValueError("check_out_date must be after check_in_date")
        if self.net_payout_amount is None:
            # Sensible default: whatever is left after platform fees.
            self.net_payout_amount = self.gross_amount - self.fees_amount
        return self


class ReservationCreate(ReservationBase):
    pass


class ReservationUpdate(BaseModel):
    unit_id: int | None = None
    guest_id: int | None = None
    guest_name: str | None = None
    check_in_date: date | None = None
    check_out_date: date | None = None
    number_of_guests: int | None = Field(default=None, ge=1, le=50)
    source: ReservationSource | None = None
    source_reference: str | None = None
    status: ReservationStatus | None = None
    gross_amount: Decimal | None = Field(default=None, ge=0)
    fees_amount: Decimal | None = Field(default=None, ge=0)
    net_payout_amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    payment_method: PaymentMethod | None = None
    payment_status: PaymentStatus | None = None
    payout_date: date | None = None
    notes: str | None = None


class ReservationRead(ORMModel):
    id: int
    property_id: int
    unit_id: int
    guest_id: int | None
    guest_name: str | None

    check_in_date: date
    check_out_date: date
    number_of_guests: int

    source: ReservationSource
    source_reference: str | None
    status: ReservationStatus

    gross_amount: Decimal
    fees_amount: Decimal
    net_payout_amount: Decimal
    currency: str
    payment_method: PaymentMethod | None
    payment_status: PaymentStatus
    payout_date: date | None

    notes: str | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def nights(self) -> int:
        return (self.check_out_date - self.check_in_date).days


class ReservationDetail(ReservationRead):
    """Reservation enriched with the labels the UI needs to avoid extra fetches."""

    property_name: str | None = None
    unit_name: str | None = None
    guest_display_name: str | None = None


# --- Daily board ----------------------------------------------------------


class DailyReservations(BaseModel):
    date: date
    property_id: int | None = None
    arrivals: list[ReservationDetail]
    departures: list[ReservationDetail]
    in_house: list[ReservationDetail]


# --- Calendar -------------------------------------------------------------


class CalendarBlock(BaseModel):
    reservation_id: int
    unit_id: int
    guest_name: str
    source: ReservationSource
    status: ReservationStatus
    check_in_date: date
    check_out_date: date
    nights: int
    #: 0-based column index within the requested month (clamped to the month).
    start_offset: int
    span_days: int
    #: True when the stay starts/ends outside the requested month.
    continues_before: bool = False
    continues_after: bool = False


class CalendarUnitRow(BaseModel):
    unit_id: int
    unit_name: str
    housekeeping_status: str
    blocks: list[CalendarBlock]


class CalendarResponse(BaseModel):
    property_id: int
    year: int
    month: int
    days_in_month: int
    first_day: date
    units: list[CalendarUnitRow]
