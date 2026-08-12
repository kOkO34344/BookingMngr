from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import HousekeepingStatus, TaskPriority, TaskStatus, TaskType
from app.schemas.common import ORMModel


class TaskBase(BaseModel):
    property_id: int
    unit_id: int | None = None
    reservation_id: int | None = None
    task_type: TaskType = TaskType.OTHER
    status: TaskStatus = TaskStatus.SCHEDULED
    priority: TaskPriority = TaskPriority.NORMAL
    assigned_to: str | None = Field(default=None, max_length=200)
    estimated_duration_minutes: int | None = Field(default=None, ge=0, le=24 * 60)
    due_date: date | None = None
    description: str | None = None
    changes_room_status_to: HousekeepingStatus | None = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    unit_id: int | None = None
    reservation_id: int | None = None
    task_type: TaskType | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assigned_to: str | None = None
    estimated_duration_minutes: int | None = Field(default=None, ge=0, le=24 * 60)
    due_date: date | None = None
    description: str | None = None
    changes_room_status_to: HousekeepingStatus | None = None


class TaskRead(ORMModel, TaskBase):
    id: int
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskDetail(TaskRead):
    property_name: str | None = None
    unit_name: str | None = None


class GenerateHousekeepingRequest(BaseModel):
    date: date
    property_id: int | None = None
    assigned_to: str | None = None
    #: Also create stayover cleans for guests staying through the date.
    include_stayovers: bool = False


class GenerateHousekeepingResponse(BaseModel):
    date: date
    created: list[TaskDetail]
    skipped_existing: int
    units_marked_dirty: list[int]
