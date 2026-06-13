from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.session import SessionCreateIn, SessionOut, SetLogIn, SetLogOut
from app.services import sessions as svc
from app.services.sessions import PlanDayNotFoundError

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut, status_code=201)
async def create_session(data: SessionCreateIn, db: AsyncSession = Depends(get_db)) -> SessionOut:
    try:
        session, suggestions = await svc.create_session(
            db, plan_day_id=data.plan_day_id, on_date=data.date
        )
    except PlanDayNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Plan day not found") from exc
    out = SessionOut.model_validate(session)
    out.suggested_targets = suggestions
    return out


@router.get("", response_model=list[SessionOut])
async def list_sessions(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
) -> list[SessionOut]:
    rows = await svc.list_sessions(db, date_from=date_from, date_to=date_to)
    return [SessionOut.model_validate(r) for r in rows]


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: int, db: AsyncSession = Depends(get_db)) -> SessionOut:
    session = await svc.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionOut.model_validate(session)


@router.post("/{session_id}/sets", response_model=SetLogOut, status_code=201)
async def add_set(session_id: int, data: SetLogIn, db: AsyncSession = Depends(get_db)) -> SetLogOut:
    log = await svc.add_set_log(db, session_id, data)
    if log is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SetLogOut.model_validate(log)


@router.patch("/{session_id}/complete", response_model=SessionOut)
async def complete_session(session_id: int, db: AsyncSession = Depends(get_db)) -> SessionOut:
    session = await svc.complete_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionOut.model_validate(session)
