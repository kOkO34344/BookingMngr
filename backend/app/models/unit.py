from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base, TimestampMixin
from app.models.enums import HousekeepingStatus, UnitStatus
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.property import Property
    from app.models.reservation import Reservation
    from app.models.task import Task


class Unit(Base, TimestampMixin):
    """A rentable room or apartment."""

    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("property_id", "name_or_number", name="uq_unit_name_per_property"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), index=True, nullable=False
    )

    name_or_number: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    capacity: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    base_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    cleaning_duration_minutes: Mapped[int] = mapped_column(
        Integer, default=settings.default_cleaning_duration_minutes, nullable=False
    )

    status: Mapped[UnitStatus] = mapped_column(
        enum_column(UnitStatus), default=UnitStatus.ACTIVE, nullable=False
    )
    housekeeping_status: Mapped[HousekeepingStatus] = mapped_column(
        enum_column(HousekeepingStatus), default=HousekeepingStatus.CLEAN, nullable=False
    )

    floor: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    property: Mapped["Property"] = relationship(back_populates="units")
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="unit")
    tasks: Mapped[list["Task"]] = relationship(back_populates="unit")
