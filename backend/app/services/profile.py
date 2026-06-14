from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserProfile
from app.schemas.profile import ProfileIn

DEFAULT_PROFILE_NAME = "Default"


class ProfileNotFoundError(Exception):
    """Raised when a requested profile id does not exist."""


class LastProfileError(Exception):
    """Raised when trying to delete the final remaining profile."""


async def get_profile(db: AsyncSession) -> UserProfile | None:
    """Return the active profile, falling back to the first profile for old data."""
    active = await db.scalar(select(UserProfile).where(UserProfile.is_active.is_(True)).limit(1))
    if active is not None:
        return active
    profile = await db.scalar(select(UserProfile).order_by(UserProfile.id).limit(1))
    if profile is not None:
        profile.is_active = True
        await db.commit()
        await db.refresh(profile)
    return profile


async def upsert_profile(db: AsyncSession, data: ProfileIn) -> UserProfile:
    """Create or update the active profile (backward-compatible /api/profile)."""
    profile = await get_profile(db)
    values = _profile_values(data)
    if profile is None:
        profile = UserProfile(name=data.name or DEFAULT_PROFILE_NAME, is_active=True, **values)
        db.add(profile)
    else:
        if data.name is not None:
            profile.name = data.name.strip()
        for key, value in values.items():
            setattr(profile, key, value)
    await db.commit()
    await db.refresh(profile)
    return profile


async def list_profiles(db: AsyncSession) -> list[UserProfile]:
    stmt = select(UserProfile).order_by(UserProfile.is_active.desc(), UserProfile.updated_at.desc())
    return list((await db.scalars(stmt)).all())


async def create_profile(db: AsyncSession, data: ProfileIn) -> UserProfile:
    has_profile = await db.scalar(select(UserProfile.id).limit(1))
    if has_profile is not None:
        await _deactivate_all(db)
    profile = UserProfile(
        name=(data.name or "New profile").strip(),
        is_active=True,
        **_profile_values(data),
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def activate_profile(db: AsyncSession, profile_id: int) -> UserProfile:
    profile = await db.get(UserProfile, profile_id)
    if profile is None:
        raise ProfileNotFoundError
    await _deactivate_all(db)
    profile.is_active = True
    await db.commit()
    await db.refresh(profile)
    return profile


async def delete_profile(db: AsyncSession, profile_id: int) -> None:
    profiles = await list_profiles(db)
    if len(profiles) <= 1:
        raise LastProfileError
    profile = next((p for p in profiles if p.id == profile_id), None)
    if profile is None:
        raise ProfileNotFoundError
    was_active = profile.is_active
    await db.delete(profile)
    await db.commit()
    if was_active:
        replacement = await db.scalar(select(UserProfile).order_by(UserProfile.id).limit(1))
        if replacement is not None:
            replacement.is_active = True
            await db.commit()


async def _deactivate_all(db: AsyncSession) -> None:
    for profile in await list_profiles(db):
        profile.is_active = False


def _profile_values(data: ProfileIn) -> dict[str, object]:
    values = data.model_dump(exclude={"name"})
    return values
