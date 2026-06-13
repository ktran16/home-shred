from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserProfile
from app.schemas.profile import ProfileIn

PROFILE_ID = 1  # single-row profile (SPEC §5)


async def get_profile(db: AsyncSession) -> UserProfile | None:
    return await db.get(UserProfile, PROFILE_ID)


async def upsert_profile(db: AsyncSession, data: ProfileIn) -> UserProfile:
    """Create or update the single profile row (id=1)."""
    profile = await db.get(UserProfile, PROFILE_ID)
    values = data.model_dump()
    if profile is None:
        profile = UserProfile(id=PROFILE_ID, **values)
        db.add(profile)
    else:
        for key, value in values.items():
            setattr(profile, key, value)
    await db.commit()
    await db.refresh(profile)
    return profile
