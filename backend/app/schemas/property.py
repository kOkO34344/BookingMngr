from datetime import datetime

from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.enums import PropertyType
from app.schemas.common import ORMModel


class PropertyBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: PropertyType = PropertyType.APARTMENT_BUILDING
    address: str | None = None
    city: str | None = None
    country: str | None = None
    timezone: str = settings.default_timezone
    notes: str | None = None


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    type: PropertyType | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    timezone: str | None = None
    notes: str | None = None
    is_archived: bool | None = None


class PropertyRead(ORMModel, PropertyBase):
    id: int
    organization_id: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class PropertyWithStats(PropertyRead):
    units_count: int = 0
