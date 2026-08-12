from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class GuestBase(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=60)
    notes: str | None = None


class GuestCreate(GuestBase):
    pass


class GuestUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=60)
    notes: str | None = None


class GuestRead(ORMModel, GuestBase):
    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime
