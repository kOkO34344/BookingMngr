"""Create the single owner account.

Run: python -m app.db.init_db

The schema itself belongs to Alembic (`alembic upgrade head`). This script
deliberately does not call `create_all`: tables built that way carry no
`alembic_version` stamp, so the first real migration would then fail with
"relation already exists" on a database that looks perfectly fine.
"""

from __future__ import annotations

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import configure_logging, logger
from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.models import Organization, User  # noqa: F401  (registers all models)


class SchemaNotReady(RuntimeError):
    """Raised when the database has not been migrated yet."""


def require_schema() -> None:
    tables = set(inspect(engine).get_table_names())
    missing = {"organizations", "users"} - tables
    if missing:
        raise SchemaNotReady(
            "Database schema is missing "
            f"({', '.join(sorted(missing))}). Run `alembic upgrade head` first."
        )


def ensure_owner(db: Session) -> User:
    org = db.scalars(select(Organization).limit(1)).first()
    if org is None:
        org = Organization(name=settings.default_organization_name)
        db.add(org)
        db.flush()
        logger.info("Created organization %s", org.name)

    user = db.scalars(
        select(User).where(User.username == settings.owner_username)
    ).first()
    if user is None:
        user = User(
            organization_id=org.id,
            username=settings.owner_username,
            email=settings.owner_email,
            full_name="Owner",
            hashed_password=hash_password(settings.owner_password),
            role="owner",
        )
        db.add(user)
        db.flush()
        logger.info("Created owner account '%s'", user.username)
    else:
        logger.info("Owner account '%s' already exists", user.username)
    return user


def main() -> None:
    configure_logging()
    require_schema()
    with SessionLocal() as db:
        ensure_owner(db)
        db.commit()
    logger.info("Database ready.")


if __name__ == "__main__":
    main()
