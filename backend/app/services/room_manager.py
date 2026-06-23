from __future__ import annotations
import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any
from collections import defaultdict
from fastapi import WebSocket
import chess
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Game, Move
from app.services.chess_service import board_from_game, board_snapshot, apply_move

log = logging.getLogger("nebula.rooms")

@dataclass
class RoomConnection:
    websocket: WebSocket
    user_id: str | None
    is_spectator: bool = False

@dataclass
class GameRoom:
    game_id: str
    board_fen: str
    connections: list[RoomConnection] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

class RoomManager:
    def __init__(self):
        self.rooms: dict[str, GameRoom] = {}
        self.user_rooms: dict[str, set[str]] = defaultdict(set)

    def get_or_create(self, game: Game) -> GameRoom:
        if game.id not in self.rooms:
            self.rooms[game.id] = GameRoom(game_id=game.id, board_fen=game.current_fen)
        return self.rooms[game.id]

    async def hydrate(self, session: AsyncSession, game_id: str) -> GameRoom | None:
        game = (await session.execute(select(Game).where(Game.id == game_id))).scalar_one_or_none()
        if not game:
            return None
        return self.get_or_create(game)

    async def join(self, room: GameRoom, websocket: WebSocket, user_id: str | None, spectator: bool = False) -> None:
        room.connections.append(RoomConnection(websocket=websocket, user_id=user_id, is_spectator=spectator))
        if user_id:
            self.user_rooms[user_id].add(room.game_id)

    async def leave(self, room: GameRoom, websocket: WebSocket) -> None:
        room.connections = [c for c in room.connections if c.websocket != websocket]

    async def broadcast(self, room: GameRoom, message: dict[str, Any]) -> None:
        disconnected = []
        for c in room.connections:
            try:
                await c.websocket.send_json(message)
            except Exception:
                disconnected.append(c)
        room.connections = [c for c in room.connections if c not in disconnected]

room_manager = RoomManager()
