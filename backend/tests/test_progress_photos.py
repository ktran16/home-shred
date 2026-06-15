"""Tests for progress photos (SPEC §19.8 W3). Files are written under a tmp media dir."""

from datetime import date
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.services import progress_photos as svc

PNG = b"\x89PNG\r\n\x1a\n" + b"fake-image-bytes"


@pytest.fixture(autouse=True)
def media_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the photo store at a throwaway dir for every test in this module."""
    monkeypatch.setattr(svc, "get_settings", lambda: Settings(media_dir=str(tmp_path)))
    return tmp_path


async def test_create_writes_file_and_row(db: AsyncSession, media_tmp: Path) -> None:
    photo = await svc.create_photo(
        db, content=PNG, content_type="image/png", on_date=date(2026, 6, 1), note="  front  "
    )
    assert photo.note == "front"  # trimmed
    stored = svc.photo_path(photo.filename)
    assert stored.exists()
    assert stored.read_bytes() == PNG


async def test_rejects_bad_type_and_oversize(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(svc.UnsupportedImageError):
        await svc.create_photo(db, content=PNG, content_type="text/plain")
    monkeypatch.setattr(svc, "MAX_PHOTO_BYTES", 4)
    with pytest.raises(svc.ImageTooLargeError):
        await svc.create_photo(db, content=PNG, content_type="image/png")


async def test_list_newest_first_and_filter(db: AsyncSession) -> None:
    await svc.create_photo(db, content=PNG, content_type="image/png", on_date=date(2026, 6, 1))
    await svc.create_photo(db, content=PNG, content_type="image/png", on_date=date(2026, 6, 10))
    rows = await svc.list_photos(db)
    assert [r.date for r in rows] == [date(2026, 6, 10), date(2026, 6, 1)]
    only = await svc.list_photos(db, date_from=date(2026, 6, 5))
    assert [r.date for r in only] == [date(2026, 6, 10)]


async def test_delete_removes_row_and_file(db: AsyncSession) -> None:
    photo = await svc.create_photo(db, content=PNG, content_type="image/jpeg")
    path = svc.photo_path(photo.filename)
    assert path.exists()
    await svc.delete_photo(db, photo.id)
    assert not path.exists()
    with pytest.raises(svc.PhotoNotFoundError):
        await svc.delete_photo(db, photo.id)


async def test_api_upload_fetch_delete(client: AsyncClient) -> None:
    posted = await client.post(
        "/api/progress/photos",
        files={"file": ("me.png", PNG, "image/png")},
        data={"date": "2026-06-02", "note": "side"},
    )
    assert posted.status_code == 201
    body = posted.json()
    assert body["note"] == "side"
    assert body["image_url"] == f"/api/progress/photos/{body['id']}/image"

    listing = (await client.get("/api/progress/photos")).json()
    assert any(p["id"] == body["id"] for p in listing)

    img = await client.get(body["image_url"])
    assert img.status_code == 200
    assert img.content == PNG
    assert img.headers["content-type"] == "image/png"

    assert (await client.delete(f"/api/progress/photos/{body['id']}")).status_code == 204
    assert (await client.delete(f"/api/progress/photos/{body['id']}")).status_code == 404


async def test_api_rejects_non_image(client: AsyncClient) -> None:
    r = await client.post(
        "/api/progress/photos",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 415
