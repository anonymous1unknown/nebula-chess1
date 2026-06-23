from __future__ import annotations
import asyncio
import json
import logging
import chess
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.rate_limit import enforce_http_rate_limit, enforce_ws_rate_limit
from app.db.session import engine, AsyncSessionLocal
from app.models import Game, Move, ChatMessage, User
from app.api.routes.auth import router as auth_router
from app.api.routes.users import router as users_router
from app.api.routes.games import router as games_router, state_from_game
from app.api.routes.health import router as health_router
from app.api.routes.tournaments import router as tournaments_router
from app.api.routes.puzzles import router as puzzles_router
from app.deps import db_session, get_current_user, ws_current_user
from app.db.base import Base
from app.services.room_manager import room_manager
from app.services.redis_pubsub import redis_bus
from app.services.chess_service import board_from_game, maybe_play_ai_move, apply_move
from app.services.stockfish_service import stockfish_service

settings = get_settings()
configure_logging()
log = logging.getLogger("nebula.app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await redis_bus.connect()
    asyncio.create_task(redis_listener_loop())
    yield
    await redis_bus.close()
    stockfish_service.close()

async def redis_listener_loop():
    if not redis_bus.redis:
        return
    pubsub = redis_bus.redis.pubsub()
    await pubsub.psubscribe("game:*")
    try:
        async for message in pubsub.listen():
            if not message or message.get("type") != "pmessage":
                continue
            channel = message.get("channel", "")
            data = message.get("data")
            if not channel or not data:
                continue
            try:
                payload = json.loads(data)
            except Exception:
                continue
            game_id = channel.split(":")[-1]
            room = room_manager.rooms.get(game_id)
            if room and payload.get("type") == "state":
                await room_manager.broadcast(room, payload)
    finally:
        await pubsub.close()

app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def headers_and_rate_limit(request, call_next):
    await enforce_http_rate_limit(request)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; connect-src 'self' ws: wss: http: https:; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline';"
    return response

app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(games_router, prefix="/api")
app.include_router(health_router)
app.include_router(tournaments_router, prefix="/api")
app.include_router(puzzles_router, prefix="/api")

@app.get("/")
async def root():
    return {"name": "Nebula Chess", "status": "running"}

@app.websocket("/ws/games/{game_id}")
async def game_ws(websocket: WebSocket, game_id: str):
    await websocket.accept()
    try:
        await enforce_ws_rate_limit(websocket)
        async with AsyncSessionLocal() as session:
            user = await ws_current_user(websocket, session)
            game = (await session.execute(select(Game).where(Game.id == game_id))).scalar_one_or_none()
            if not game:
                await websocket.send_json({"type": "error", "message": "Game not found"})
                await websocket.close(code=4404)
                return
            room = room_manager.get_or_create(game)
            spectator = user.id not in [game.white_id, game.black_id]
            await room_manager.join(room, websocket, user.id, spectator=spectator)
            await websocket.send_json({"type": "state", "state": state_from_game(game, spectators=max(0, len(room.connections) - 2)).model_dump()})
            await websocket.send_json({"type": "chat_history", "messages": []})

            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type")
                if msg_type == "move":
                    async with room.lock:
                        game = (await session.execute(select(Game).where(Game.id == game_id))).scalar_one_or_none()
                        if not game:
                            await websocket.send_json({"type": "error", "message": "Game not found"})
                            continue
                        if user.id not in [game.white_id, game.black_id]:
                            await websocket.send_json({"type": "error", "message": "Spectators cannot move"})
                            continue
                        board = board_from_game(game)
                        expected_turn_id = game.white_id if board.turn == chess.WHITE else game.black_id
                        if expected_turn_id != user.id:
                            await websocket.send_json({"type": "error", "message": "Not your turn"})
                            continue
                        from app.schemas import MoveRequest
                        payload = MoveRequest(**data)
                        try:
                            game, move_row, diff = await apply_move(session, game, user.id, payload.uci, payload.duration_ms)
                            ai_result = await maybe_play_ai_move(session, game)
                            if ai_result:
                                game, ai_move, ai_diff = ai_result
                        except Exception as e:
                            await websocket.send_json({"type": "error", "message": str(e)})
                            await session.rollback()
                            continue
                        await session.commit()
                        state = state_from_game(game, spectators=max(0, len(room.connections) - 2)).model_dump()
                        await room_manager.broadcast(room, {"type": "state", "state": state})
                        if redis_bus.redis:
                            await redis_bus.publish(f"game:{game.id}", {"type": "state", "state": state})
                elif msg_type == "chat":
                    content = str(data.get("content", ""))[:500]
                    from app.models import ChatMessage
                    session.add(ChatMessage(game_id=game_id, sender_id=user.id, content=content, is_system=False))
                    await session.commit()
                    await room_manager.broadcast(room, {"type": "chat", "sender_id": user.id, "content": content})
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "resync":
                    game = (await session.execute(select(Game).where(Game.id == game_id))).scalar_one_or_none()
                    if game:
                        await websocket.send_json({"type": "state", "state": state_from_game(game, spectators=max(0, len(room.connections) - 2)).model_dump()})
                else:
                    await websocket.send_json({"type": "error", "message": "Unknown message type"})
    except WebSocketDisconnect:
        pass
    finally:
        try:
            async with AsyncSessionLocal() as session:
                game = (await session.execute(select(Game).where(Game.id == game_id))).scalar_one_or_none()
                if game:
                    room = room_manager.get_or_create(game)
                    await room_manager.leave(room, websocket)
        except Exception:
            pass
