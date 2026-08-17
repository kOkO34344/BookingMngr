from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.ratelimit import login_limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.models.organization import User
from app.schemas.auth import LoginRequest, PasswordChangeRequest, Token, UserRead
from app.schemas.common import Message

router = APIRouter(prefix="/auth", tags=["auth"])


def _attempt_key(request: Request, username: str) -> str:
    """Rate-limit bucket. Relies on uvicorn's --proxy-headers behind Caddy."""
    client = request.client.host if request.client else "unknown"
    return f"{client}:{username.lower()}"


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, request: Request, db: DbSession) -> Token:
    key = _attempt_key(request, payload.username)
    wait = login_limiter.retry_after(key)
    if wait is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed sign-in attempts. Try again shortly.",
            headers={"Retry-After": str(wait)},
        )

    user = db.scalars(select(User).where(User.username == payload.username)).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        login_limiter.record_failure(key)
        # Same message for unknown user and bad password.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")

    login_limiter.reset(key)
    token = create_access_token(user.id, organization_id=user.organization_id)
    return Token(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/change-password", response_model=Message)
def change_password(
    payload: PasswordChangeRequest, user: CurrentUser, db: DbSession
) -> Message:
    """Let the account holder rotate their own password.

    Without this the bootstrap password from OWNER_PASSWORD is permanent:
    `init_db.ensure_owner` only sets a password when it creates the account.
    """
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current one",
        )

    user.hashed_password = hash_password(payload.new_password)
    db.add(user)
    # Existing tokens stay valid: they are signed with SECRET_KEY and carry no
    # password material. Single user on a private host, so that is acceptable;
    # revoking would need a token version column on User.
    return Message(detail="Password updated.")


@router.get("/me", response_model=UserRead)
def read_me(user: CurrentUser) -> User:
    return user
