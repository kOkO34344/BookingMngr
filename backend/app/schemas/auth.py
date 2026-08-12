from pydantic import BaseModel

from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserRead(ORMModel):
    id: int
    organization_id: int
    username: str
    email: str | None = None
    full_name: str | None = None
    role: str
    is_active: bool
