"""Progress photos (SPEC §19.8 W3).

Image bytes are written to disk under the configured media dir; the DB stores only
metadata. The service takes raw bytes (not an UploadFile) so it stays HTTP-agnostic and
unit-testable; the router adapts the upload. The only feature touching file storage —
content type and size are validated explicitly.
"""

import uuid
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import ProgressPhoto

# rationale (SPEC §19.8 W3): accept the common phone-camera formats; cap size so a stray
# upload can't fill the host disk.
ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
MAX_PHOTO_BYTES = 10 * 1024 * 1024  # 10 MB
_SUBDIR = "progress"


class UnsupportedImageError(Exception):
    """Upload is not an allowed image content type."""


class ImageTooLargeError(Exception):
    """Upload exceeds the size limit."""


class PhotoNotFoundError(Exception):
    """No progress photo with the given id."""


def _media_root() -> Path:
    return Path(get_settings().media_dir) / _SUBDIR


def photo_path(filename: str) -> Path:
    return _media_root() / filename


async def create_photo(
    db: AsyncSession,
    *,
    content: bytes,
    content_type: str,
    on_date: date | None = None,
    note: str | None = None,
) -> ProgressPhoto:
    ext = ALLOWED_CONTENT_TYPES.get(content_type)
    if ext is None:
        raise UnsupportedImageError(content_type)
    if len(content) > MAX_PHOTO_BYTES:
        raise ImageTooLargeError(len(content))

    root = _media_root()
    root.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{ext}"
    (root / filename).write_bytes(content)

    photo = ProgressPhoto(
        date=on_date or date.today(),
        filename=filename,
        content_type=content_type,
        note=(note.strip() if note and note.strip() else None),
    )
    db.add(photo)
    await db.commit()
    await db.refresh(photo)
    return photo


async def list_photos(
    db: AsyncSession, *, date_from: date | None = None, date_to: date | None = None
) -> list[ProgressPhoto]:
    stmt = select(ProgressPhoto)
    if date_from is not None:
        stmt = stmt.where(ProgressPhoto.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(ProgressPhoto.date <= date_to)
    # newest first for the gallery
    stmt = stmt.order_by(ProgressPhoto.date.desc(), ProgressPhoto.id.desc())
    return list((await db.scalars(stmt)).all())


async def get_photo(db: AsyncSession, photo_id: int) -> ProgressPhoto | None:
    return await db.get(ProgressPhoto, photo_id)


async def delete_photo(db: AsyncSession, photo_id: int) -> None:
    photo = await db.get(ProgressPhoto, photo_id)
    if photo is None:
        raise PhotoNotFoundError(photo_id)
    path = photo_path(photo.filename)
    await db.delete(photo)
    await db.commit()
    path.unlink(missing_ok=True)  # best-effort; row is the source of truth
