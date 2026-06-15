from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.metrics import ExerciseStrengthOut, LoadPredictionOut, VolumePoint
from app.schemas.progress_photo import ProgressPhotoOut
from app.services import prediction as prediction_svc
from app.services import progress_photos as photos_svc
from app.services import strength as strength_svc
from app.services import volume as svc

router = APIRouter(prefix="/progress", tags=["progress"])


def _photo_out(photo: photos_svc.ProgressPhoto) -> ProgressPhotoOut:
    return ProgressPhotoOut(
        id=photo.id,
        date=photo.date,
        note=photo.note,
        content_type=photo.content_type,
        created_at=photo.created_at,
        image_url=f"/api/progress/photos/{photo.id}/image",
    )


@router.get("/volume", response_model=list[VolumePoint])
async def volume(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
) -> list[VolumePoint]:
    points = await svc.weekly_volume(db, date_from=date_from, date_to=date_to)
    return [VolumePoint(week=p.week, muscle=p.muscle, volume=p.volume) for p in points]


@router.get("/strength", response_model=list[ExerciseStrengthOut])
async def strength(db: AsyncSession = Depends(get_db)) -> list[ExerciseStrengthOut]:
    rows = await strength_svc.exercise_strength(db)
    return [ExerciseStrengthOut.model_validate(r) for r in rows]


@router.get("/prediction", response_model=list[LoadPredictionOut])
async def prediction(db: AsyncSession = Depends(get_db)) -> list[LoadPredictionOut]:
    """Per-exercise next-session load / readiness forecast (SPEC §17.3 A2)."""
    rows = await prediction_svc.exercise_predictions(db)
    return [LoadPredictionOut.model_validate(r) for r in rows]


@router.get("/photos", response_model=list[ProgressPhotoOut])
async def list_photos(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
) -> list[ProgressPhotoOut]:
    """List progress photos, newest first (SPEC §19.8 W3)."""
    rows = await photos_svc.list_photos(db, date_from=date_from, date_to=date_to)
    return [_photo_out(p) for p in rows]


@router.post("/photos", response_model=ProgressPhotoOut, status_code=201)
async def upload_photo(
    file: UploadFile = File(...),
    photo_date: date | None = Form(default=None, alias="date"),
    note: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
) -> ProgressPhotoOut:
    content = await file.read()
    try:
        photo = await photos_svc.create_photo(
            db,
            content=content,
            content_type=file.content_type or "",
            on_date=photo_date,
            note=note,
        )
    except photos_svc.UnsupportedImageError as exc:
        raise HTTPException(
            status_code=415, detail="Unsupported image type (use JPEG/PNG/WebP)"
        ) from exc
    except photos_svc.ImageTooLargeError as exc:
        raise HTTPException(status_code=413, detail="Image too large (max 10 MB)") from exc
    return _photo_out(photo)


@router.get("/photos/{photo_id}/image")
async def photo_image(photo_id: int, db: AsyncSession = Depends(get_db)) -> FileResponse:
    photo = await photos_svc.get_photo(db, photo_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    path = photos_svc.photo_path(photo.filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image file missing")
    return FileResponse(path, media_type=photo.content_type)


@router.delete("/photos/{photo_id}", status_code=204)
async def delete_photo(photo_id: int, db: AsyncSession = Depends(get_db)) -> None:
    try:
        await photos_svc.delete_photo(db, photo_id)
    except photos_svc.PhotoNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Photo not found") from exc
