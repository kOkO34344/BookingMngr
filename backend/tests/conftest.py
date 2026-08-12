"""Test wiring.

Defaults to in-memory SQLite so `pytest` needs no running services. Set
TEST_DATABASE_URL to run the same suite against the real target:

    docker compose up -d db
    TEST_DATABASE_URL=postgresql+psycopg://bookingmngr:bookingmngr@localhost:5432/bookingmngr_test \\
        .venv/bin/python -m pytest tests -q

Worth doing before a release: SQLite is lenient about things Postgres is not
(type affinity, constraint timing), so a green SQLite run is necessary but not
sufficient.
"""

import os
from collections.abc import Generator

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:"
)
# Point the app's own engine at the same place, so anything that slips past the
# get_db override fails loudly here instead of touching a development database.
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Organization, User  # noqa: F401
from app.core.security import hash_password

if TEST_DATABASE_URL.startswith("sqlite"):
    # One connection shared by every session, or the in-memory schema vanishes.
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(TEST_DATABASE_URL, poolclass=StaticPool)
    # `create_all` builds the schema here rather than Alembic, so the extension
    # the overlap exclusion constraint depends on has to be installed by hand —
    # the migration that normally does it never runs in tests.
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def owner(db: Session) -> User:
    org = Organization(name="Test Org")
    db.add(org)
    db.flush()
    user = User(
        organization_id=org.id,
        username="owner",
        hashed_password=hash_password("secret"),
        role="owner",
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture
def client(db: Session, owner: User) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        response = test_client.post(
            f"{settings.api_v1_prefix}/auth/login",
            json={"username": "owner", "password": "secret"},
        )
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
        test_client.headers["Authorization"] = f"Bearer {token}"
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def api() -> str:
    return settings.api_v1_prefix
