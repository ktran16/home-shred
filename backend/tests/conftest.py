"""Shared pytest fixtures.

Uses a dedicated test database (TEST_DATABASE_URL, never the dev DB). The schema
is created once per session from the ORM metadata; every table is truncated after
each test so state doesn't leak between tests (services issue real commits).
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401  (populate metadata before create_all)
from app.config import get_settings
from app.db import Base, get_db
from app.main import app as fastapi_app


@pytest_asyncio.fixture
async def engine():
    """Function-scoped engine with a fresh schema (asyncpg connections are bound to
    the running event loop, so a session-scoped engine would cross loops)."""
    eng = create_async_engine(get_settings().test_database_url, future=True, poolclass=NullPool)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine) -> AsyncGenerator[AsyncSession]:
    sessionmaker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """HTTP client with get_db overridden to the test session."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"
