"""Shared pytest fixtures.

Uses a dedicated test database (TEST_DATABASE_URL, never the dev DB). The schema
is created once per session from the ORM metadata; each test runs inside a
transaction that is rolled back, so tests don't leak state.
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.db import Base, get_db
from app.main import app

# Import models so metadata is populated before create_all.
import app.models  # noqa: F401


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(get_settings().test_database_url, future=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession]:
    """A session bound to a transaction that is rolled back after each test."""
    connection = await engine.connect()
    trans = await connection.begin()
    session = async_sessionmaker(bind=connection, expire_on_commit=False)()
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """HTTP client with get_db overridden to the rolled-back test session."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"
