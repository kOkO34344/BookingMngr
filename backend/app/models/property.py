from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.base import Base, TimestampMixin
from app.models.enums import PropertyType
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.reservation import Reservation
    from app.models.task import Task
    from app.models.unit import Unit


class Property(Base, TimestampMixin):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[PropertyType] = mapped_column(
        enum_column(PropertyType), default=PropertyType.APARTMENT_BUILDING, nullable=False
    )
    address: Mapped[str | None] = mapped_column(String(400), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(64), default=settings.default_timezone, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Soft delete: DELETE /properties/{id} archives instead of destroying history.
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    units: Mapped[list["Unit"]] = relationship(
        back_populates="property", cascade="all, delete-orphan"
    )
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="property")
    tasks: Mapped[list["Task"]] = relationship(back_populates="property")
