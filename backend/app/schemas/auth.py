from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

#: Short enough not to annoy a single trusted user, long enough to matter.
MIN_PASSWORD_LENGTH = 10


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=200)


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
