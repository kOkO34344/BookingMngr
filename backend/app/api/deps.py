"""Shared FastAPI dependencies: DB session, current user, tenant scope."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.organization import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login", auto_error=False
)

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession, token: Annotated[str | None, Depends(oauth2_scheme)]
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_error

    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise credentials_error

    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_organization_id(user: CurrentUser) -> int:
    """The tenant scope for the request.

    Single-tenant today, so this is just the owner's organization. Every query
    in the service layer filters by it, which is what makes multi-tenant a
    configuration change rather than a rewrite.
    """
    return user.organization_id


OrganizationId = Annotated[int, Depends(get_organization_id)]


def get_actor(user: CurrentUser) -> str:
    """Human-readable actor label for the audit trail."""
    return user.username


Actor = Annotated[str, Depends(get_actor)]
