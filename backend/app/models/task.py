from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import HousekeepingStatus, TaskPriority, TaskStatus, TaskType
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.property import Property
    from app.models.reservation import Reservation
    from app.models.unit import Unit


class Task(Base, TimestampMixin):
    """Housekeeping and maintenance work item."""

    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_property_due", "property_id", "due_date"),
        Index("ix_tasks_unit_due", "unit_id", "due_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"), index=True, nullable=False
    )
    #: Null for common areas (lobby, stairwell, garden).
    unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("units.id", ondelete="CASCADE"), index=True, nullable=True
    )
    reservation_id: Mapped[int | None] = mapped_column(
        ForeignKey("reservations.id", ondelete="SET NULL"), index=True, nullable=True
    )

    task_type: Mapped[TaskType] = mapped_column(
        enum_column(TaskType), default=TaskType.OTHER, nullable=False, index=True
    )
    status: Mapped[TaskStatus] = mapped_column(
        enum_column(TaskStatus), default=TaskStatus.SCHEDULED, nullable=False, index=True
    )
    priority: Mapped[TaskPriority] = mapped_column(
        enum_column(TaskPriority), default=TaskPriority.NORMAL, nullable=False
    )

    #: Free-text for now (manager or worker name); becomes an FK when staff
    #: accounts exist.
    assigned_to: Mapped[str | None] = mapped_column(String(200), nullable=True)

    estimated_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    due_date: Mapped[date | None] = mapped_column(nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: When set, completing this task moves the unit to this housekeeping status.
    changes_room_status_to: Mapped[HousekeepingStatus | None] = mapped_column(
        enum_column(HousekeepingStatus), nullable=True
    )

    property: Mapped["Property"] = relationship(back_populates="tasks")
    unit: Mapped["Unit | None"] = relationship(back_populates="tasks")
    reservation: Mapped["Reservation | None"] = relationship(back_populates="tasks")
