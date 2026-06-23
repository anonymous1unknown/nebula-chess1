from __future__ import annotations
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.security import create_token, hash_password, verify_password
from app.deps import db_session, get_current_user
from app.models import RefreshToken, User, AuditEvent
from app.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

def user_public(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        rating_blitz=user.rating_blitz,
        rating_rapid=user.rating_rapid,
        rating_classical=user.rating_classical,
        created_at=user.created_at,
    )

def issue_token_pair(user: User, session: AsyncSession) -> TokenResponse:
    access = create_token({"sub": user.id, "type": "access"}, timedelta(minutes=settings.access_token_expire_minutes))
    refresh_jti = token_urlsafe(24)
    refresh = create_token({"sub": user.id, "type": "refresh", "jti_hint": refresh_jti}, timedelta(days=settings.refresh_token_expire_days))
    session.add(RefreshToken(
        user_id=user.id,
        jti=refresh_jti,
        token_hash=hash_password(refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    ))
    return TokenResponse(access_token=access, refresh_token=refresh)

@router.post("/register", response_model=TokenResponse)
async def register(payload: RegisterRequest, request: Request, session: AsyncSession = Depends(db_session)):
    existing = (await session.execute(select(User).where(or_(User.email == payload.email, User.username == payload.username)))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email or username already exists")
    user = User(email=payload.email, username=payload.username, display_name=payload.display_name, password_hash=hash_password(payload.password))
    session.add(user)
    await session.flush()
    session.add(AuditEvent(actor_user_id=user.id, event_type="register", severity="info", ip_address=request.client.host if request.client else None))
    tokens = issue_token_pair(user, session)
    await session.commit()
    return tokens

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, session: AsyncSession = Depends(db_session)):
    user = (await session.execute(select(User).where(or_(User.email == payload.login, User.username == payload.login)))).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    session.add(AuditEvent(actor_user_id=user.id, event_type="login", severity="info", ip_address=request.client.host if request.client else None))
    tokens = issue_token_pair(user, session)
    await session.commit()
    return tokens

@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, request: Request, session: AsyncSession = Depends(db_session)):
    from jose import JWTError
    from app.core.security import decode_token
    try:
        decoded = decode_token(payload.refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token type")
    user_id = decoded.get("sub")
    jti_hint = decoded.get("jti_hint")
    row = (await session.execute(select(RefreshToken).where(RefreshToken.jti == jti_hint, RefreshToken.revoked_at.is_(None)))).scalar_one_or_none()
    if not row or not verify_password(payload.refresh_token, row.token_hash):
        raise HTTPException(status_code=401, detail="Refresh token revoked")
    row.revoked_at = datetime.now(timezone.utc)
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    tokens = issue_token_pair(user, session)
    await session.commit()
    return tokens

@router.get("/me", response_model=UserPublic)
async def me(user: User = Depends(get_current_user)):
    return user_public(user)
