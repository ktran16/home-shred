from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.measurement import (
    MeasurementEntryIn,
    MeasurementEntryOut,
    MeasurementSeriesOut,
    MeasurementSeriesPointOut,
    MeasurementTypeIn,
    MeasurementTypeOut,
)
from app.services import measurements as svc

router = APIRouter(prefix="/measurements", tags=["measurements"])


@router.get("/types", response_model=list[MeasurementTypeOut])
async def list_types(db: AsyncSession = Depends(get_db)) -> list[MeasurementTypeOut]:
    return [MeasurementTypeOut.model_validate(t) for t in await svc.list_types(db)]


@router.post("/types", response_model=MeasurementTypeOut, status_code=201)
async def create_type(
    data: MeasurementTypeIn, db: AsyncSession = Depends(get_db)
) -> MeasurementTypeOut:
    try:
        mtype = await svc.create_type(db, data)
    except svc.DuplicateMeasurementTypeError as exc:
        raise HTTPException(
            status_code=409, detail="A measurement with that name already exists"
        ) from exc
    return MeasurementTypeOut.model_validate(mtype)


@router.delete("/types/{type_id}", status_code=204)
async def delete_type(type_id: int, db: AsyncSession = Depends(get_db)) -> None:
    try:
        await svc.delete_type(db, type_id)
    except svc.MeasurementTypeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Measurement type not found") from exc
    except svc.BuiltinMeasurementTypeError as exc:
        raise HTTPException(
            status_code=409, detail="Built-in measurements cannot be deleted"
        ) from exc


@router.get("/entries", response_model=list[MeasurementEntryOut])
async def list_entries(
    type_id: int | None = None,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
) -> list[MeasurementEntryOut]:
    rows = await svc.list_entries(db, type_id=type_id, date_from=date_from, date_to=date_to)
    return [MeasurementEntryOut.model_validate(r) for r in rows]


@router.post("/entries", response_model=MeasurementEntryOut, status_code=201)
async def upsert_entry(
    data: MeasurementEntryIn, db: AsyncSession = Depends(get_db)
) -> MeasurementEntryOut:
    try:
        entry = await svc.upsert_entry(db, data)
    except svc.MeasurementTypeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Measurement type not found") from exc
    return MeasurementEntryOut.model_validate(entry)


@router.delete("/entries/{entry_id}", status_code=204)
async def delete_entry(entry_id: int, db: AsyncSession = Depends(get_db)) -> None:
    try:
        await svc.delete_entry(db, entry_id)
    except svc.MeasurementEntryNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Measurement entry not found") from exc


@router.get("/series", response_model=list[MeasurementSeriesOut])
async def series(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
) -> list[MeasurementSeriesOut]:
    return [
        MeasurementSeriesOut(
            type=MeasurementTypeOut.model_validate(s.type),
            points=[MeasurementSeriesPointOut(date=e.date, value=e.value) for e in s.entries],
            latest=s.latest,
            change=s.change,
        )
        for s in await svc.measurement_series(db, date_from=date_from, date_to=date_to)
    ]
