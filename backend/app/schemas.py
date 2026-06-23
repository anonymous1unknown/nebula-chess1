from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Any, Literal

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=80)

class LoginRequest(BaseModel):
    login: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class UserPublic(BaseModel):
    id: str
    email: EmailStr
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    rating_blitz: int
    rating_rapid: int
    rating_classical: int
    created_at: datetime

class ProfileUpdate(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    country: str | None = None
    avatar_url: str | None = None

class GameCreateRequest(BaseModel):
    time_control_seconds: int = 600
    increment_seconds: int = 0
    variant: str = "standard"
    play_as: Literal["white", "black", "random", "any"] = "any"
    against_ai: bool = False

class GameJoinRequest(BaseModel):
    invite_code: str

class MoveRequest(BaseModel):
    uci: str
    client_move_id: str | None = None
    duration_ms: int | None = None

class ChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)

class GameState(BaseModel):
    game_id: str
    status: str
    white_id: str | None
    black_id: str | None
    current_fen: str
    pgn: str
    turn: str
    last_move_uci: str | None = None
    legal_moves: list[str] = []
    selected_square: str | None = None
    white_clock_ms: int
    black_clock_ms: int
    result: str | None = None
    winner_id: str | None = None
    move_count: int
    spectators: int = 0
    updated_at: datetime | None = None

class MoveOut(BaseModel):
    ply: int
    move_number: int
    uci: str
    san: str
    fen_before: str
    fen_after: str
    created_at: datetime
    user_id: str | None = None

class GameSummary(BaseModel):
    id: str
    invite_code: str
    status: str
    white_id: str | None
    black_id: str | None
    current_fen: str
    result: str | None
    created_at: datetime

class LeaderboardRow(BaseModel):
    rank: int
    user: UserPublic
    rating: int
    wins: int
    losses: int
    draws: int

class SpectateJoinResponse(BaseModel):
    game_id: str
    room_token: str | None = None

class AnalysisResponse(BaseModel):
    game_id: str
    evaluation_cp: int | None = None
    best_move: str | None = None
    principal_variation: list[str] = []
    cheat_score: float | None = None
    cheat_reason: str | None = None
