from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.enums import HousekeepingStatus, UnitStatus
from app.schemas.common import ORMModel


class UnitBase(BaseModel):
    name_or_number: str = Field(min_length=1, max_length=100)
    unit_type: str | None = None
    capacity: int = Field(default=2, ge=1, le=50)
    base_price: Decimal | None = Field(default=None, ge=0)
    cleaning_duration_minutes: int = Field(
        default=settings.default_cleaning_duration_minutes, ge=0, le=24 * 60
    )
    status: UnitStatus = UnitStatus.ACTIVE
    housekeeping_status: HousekeepingStatus = HousekeepingStatus.CLEAN
    floor: str | None = None
    notes: str | None = None


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseModel):
    name_or_number: str | None = Field(default=None, min_length=1, max_length=100)
    unit_type: str | None = None
    capacity: int | None = Field(default=None, ge=1, le=50)
    base_price: Decimal | None = Field(default=None, ge=0)
    cleaning_duration_minutes: int | None = Field(default=None, ge=0, le=24 * 60)
    status: UnitStatus | None = None
    housekeeping_status: HousekeepingStatus | None = None
    floor: str | None = None
    notes: str | None = None
    is_archived: bool | None = None


class UnitRead(ORMModel, UnitBase):
    id: int
    property_id: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime
