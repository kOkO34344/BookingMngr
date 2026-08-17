"""Reset a user's password from the server.

Run: python -m app.db.reset_password [--username owner]

This is the recovery path when the only account is locked out — the
`/auth/change-password` endpoint needs the current password, and
`init_db.ensure_owner` will not touch an account that already exists.

The password is read from a prompt (never echoed) or, for non-interactive use,
from the NEW_PASSWORD environment variable. It is deliberately not a command
line argument, which would land in the shell history and the process list.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import configure_logging, logger
from app.core.security import hash_password
from app.db.init_db import require_schema
from app.db.session import SessionLocal
from app.models.organization import User
from app.schemas.auth import MIN_PASSWORD_LENGTH


def _read_new_password() -> str:
    from_env = os.environ.get("NEW_PASSWORD")
    if from_env:
        return from_env

    if not sys.stdin.isatty():
        raise SystemExit(
            "No TTY to prompt on. Set NEW_PASSWORD in the environment instead."
        )
    first = getpass.getpass("New password: ")
    if first != getpass.getpass("Repeat new password: "):
        raise SystemExit("Passwords did not match.")
    return first


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset a user's password.")
    parser.add_argument(
        "--username",
        default=settings.owner_username,
        help="Account to reset (defaults to OWNER_USERNAME).",
    )
    args = parser.parse_args()

    configure_logging()
    require_schema()

    password = _read_new_password()
    if len(password) < MIN_PASSWORD_LENGTH:
        raise SystemExit(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    with SessionLocal() as db:
        user = db.scalars(select(User).where(User.username == args.username)).first()
        if user is None:
            raise SystemExit(f"No such user: {args.username}")
        user.hashed_password = hash_password(password)
        db.add(user)
        db.commit()

    logger.info("Password updated for '%s'.", args.username)


if __name__ == "__main__":
    main()
