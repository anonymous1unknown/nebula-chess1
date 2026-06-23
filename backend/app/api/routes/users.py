from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import db_session, get_current_user
from app.models import User, Game, Move, RatingHistory, Friendship, Achievement, UserAchievement
from app.schemas import ProfileUpdate, UserPublic, LeaderboardRow
from app.api.routes.auth import user_public

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/profile/{username}", response_model=UserPublic)
async def profile(username: str, session: AsyncSession = Depends(db_session)):
    user = (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user_public(user)

@router.patch("/me", response_model=UserPublic)
async def update_me(payload: ProfileUpdate, session: AsyncSession = Depends(db_session), user: User = Depends(get_current_user)):
    for field in ["display_name", "bio", "country", "avatar_url"]:
        value = getattr(payload, field)
        if value is not None:
            setattr(user, field, value)
    await session.commit()
    await session.refresh(user)
    return user_public(user)

@router.get("/leaderboard", response_model=list[LeaderboardRow])
async def leaderboard(mode: str = "blitz", limit: int = 20, session: AsyncSession = Depends(db_session)):
    rating_col = {"blitz": User.rating_blitz, "rapid": User.rating_rapid, "classical": User.rating_classical}.get(mode, User.rating_blitz)
    stmt = select(User, rating_col.label("rating")).order_by(rating_col.desc()).limit(limit)
    rows = (await session.execute(stmt)).all()
    out = []
    for idx, (user, rating) in enumerate(rows, start=1):
        wins = 0
        losses = 0
        draws = 0
        out.append(LeaderboardRow(rank=idx, user=user_public(user), rating=rating, wins=wins, losses=losses, draws=draws))
    return out

@router.get("/me/history")
async def my_history(session: AsyncSession = Depends(db_session), user: User = Depends(get_current_user)):
    games = (await session.execute(select(Game).where((Game.white_id == user.id) | (Game.black_id == user.id)).order_by(Game.created_at.desc()).limit(50))).scalars().all()
    return [{"id": g.id, "result": g.result, "created_at": g.created_at, "current_fen": g.current_fen, "status": g.status.value} for g in games]
