from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import db_session, get_current_user
from app.models import Tournament, User

router = APIRouter(prefix="/tournaments", tags=["tournaments"])

@router.get("")
async def list_tournaments(session: AsyncSession = Depends(db_session), user: User = Depends(get_current_user)):
    rows = (await session.execute(select(Tournament).order_by(Tournament.created_at.desc()).limit(50))).scalars().all()
    return [{"id": t.id, "name": t.name, "status": t.status, "starts_at": t.starts_at, "ends_at": t.ends_at, "description": t.description} for t in rows]

@router.post("")
async def create_tournament(payload: dict, session: AsyncSession = Depends(db_session), user: User = Depends(get_current_user)):
    t = Tournament(name=payload.get("name", "Nebula Cup"), description=payload.get("description"), created_by=user.id, status=payload.get("status", "scheduled"))
    session.add(t)
    await session.commit()
    return {"id": t.id, "name": t.name, "status": t.status}
