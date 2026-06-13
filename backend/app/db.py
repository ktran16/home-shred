from collections.abc import AsyncGenerator
from enum import StrEnum

from sqlalchemy import Enum as SAEnum
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(AsyncAttrs, DeclarativeBase):
    """Declarative base for all ORM models."""


def enum_col(enum_cls: type[StrEnum], length: int = 32) -> SAEnum:
    """Column type for a StrEnum stored as its *value* text (CLAUDE.md: store as text).

    native_enum=False → VARCHAR + CHECK; values_callable forces SQLAlchemy to
    persist `member.value` (e.g. "dumbbell") rather than the member name.
    """
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda e: [m.value for m in e],
    )


_settings = get_settings()
engine = create_async_engine(_settings.database_url, echo=False, future=True)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency yielding an async session."""
    async with async_session() as session:
        yield session
