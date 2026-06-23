from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import db_session, get_current_user
from app.models import Game, GameStatus, Move, ChatMessage, User, AuditEvent, Invitation, InvitationStatus
from app.schemas import GameCreateRequest, GameJoinRequest, MoveRequest, ChatRequest, GameSummary, GameState, MoveOut, AnalysisResponse
from app.services.chess_service import board_from_game, board_snapshot, apply_move, maybe_play_ai_move
from app.services.anti_cheat import evaluate_cheat_risk, maybe_flag_cheat
from app.services.stockfish_service import stockfish_service
from app.services.room_manager import room_manager
from app.services.redis_pubsub import redis_bus
import chess

router = APIRouter(prefix="/games", tags=["games"])

def to_summary(g: Game) -> GameSummary:
    return GameSummary(id=g.id, invite_code=g.invite_code, status=g.status.value, white_id=g.white_id, black_id=g.black_id, current_fen=g.current_fen, result=g.result, created_at=g.created_at)

def state_from_game(game: Game, spectators: int = 0) -> GameState:
    board = board_from_game(game)
    snap = board_snapshot(board)
    return GameState(
        game_id=game.id,
        status=game.status.value,
        white_id=game.white_id,
        black_id=game.black_id,
        current_fen=game.current_fen,
        pgn=game.pgn,
        turn=game.turn,
        legal_moves=snap["legal_moves"],
        white_clock_ms=game.white_clock_ms,
        black_clock_ms=game.black_clock_ms,
        result=game.result,
        winner_id=game.winner_id,
        move_count=game.move_count,
        spectators=spectators,
        updated_at=game.updated_at,
    )

@router.post("", response_model=GameSummary)
async def create_game(payload: GameCreateRequest, session: AsyncSession = Depends(db_session), user: User = Depends(get_current_user)):
    code = token_urlsafe(8).replace("-", "").replace("_", "")[:12]
    game = Game(
        invite_code=code,
        creator_id=user.id,
        white_id=user.id if payload.play_as in ("white", "any") else None,
        black_id=None if payload.play_as in ("white", "any") else user.id if payload.play_as == "black" else None,
        status=GameStatus.active if payload.against_ai else GameStatus.waiting,
        time_control_seconds=payload.time_control_seconds,
        increment_seconds=payload.increment_seconds,
        white_clock_ms=payload.time_control_seconds * 1000,
        black_clock_ms=payload.time_control_seconds * 1000,
        game_metadata={"against_ai": payload.against_ai, "created_by": user.username},
    )
    session.add(game)
    await session.flush()
    if payload.against_ai and payload.play_as == "black":
        await maybe_play_ai_move(session, game)
    room_manager.get_or_create(game)
    await session.commit()
    return to_summary(game)

@router.post("/join", response_model=GameSummary)
async def join_game(payload: GameJoinRequest, session: AsyncSession = Depends(db_session), user: User = Depends(get_current_user)):
    game = (await session.execute(select(Game).where(Game.invite_code == payload.invite_code))).scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.white_id is None:
        game.white_id = user.id
    elif game.black_id is None and game.white_id != user.id:
        game.black_id = user.id
    if game.white_id and game.black_id:
        game.status = GameStatus.active
    await session.commit()
    return to_summary(game)

@router.get("/{game_id}", response_model=GameState)
async def get_game(game_id: str, session: AsyncSession = Depends(db_session), user: User = Depends(get_current_user)):
    game = (await session.execute(select(Game).where(Game.id == game_id))).scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return state_from_game(game)

@router.get("/{game_id}/moves", response_model=list[MoveOut])
async def get_moves(game_id: str, session: AsyncSession = Depends(db_session), user: User = Depends(get_current_user)):
    moves = (await session.execute(select(Move).where(Move.game_id == game_id).order_by(Move.ply.asc()))).scalars().all()
    return [MoveOut(ply=m.ply, move_number=m.move_number, uci=m.uci, san=m.san, fen_before=m.fen_before, fen_after=m.fen_after, created_at=m.created_at, user_id=m.user_id) for m in moves]

@router.post("/{game_id}/move", response_model=GameState)
async def make_move(game_id: str, payload: MoveRequest, session: AsyncSession = Depends(db_session), user: User = Depends(get_current_user)):
    game = (await session.execute(select(Game).where(Game.id == game_id))).scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.status == GameStatus.finished:
        raise HTTPException(status_code=409, detail="Game already finished")
    if user.id not in [game.white_id, game.black_id]:
        raise HTTPException(status_code=403, detail="You are not a player in this game")
    board = board_from_game(game)
    expected_turn_id = game.white_id if board.turn == chess.WHITE else game.black_id
    if expected_turn_id != user.id:
        raise HTTPException(status_code=409, detail="Not your turn")
    try:
        game, move_row, diff = await apply_move(session, game, user.id, payload.uci, payload.duration_ms)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    ai_game, ai_move, ai_diff = await maybe_play_ai_move(session, game)
    moves = (await session.execute(select(Move).where(Move.game_id == game.id).order_by(Move.ply.asc()))).scalars().all()
    assessment = evaluate_cheat_risk(game, moves, engine_best_moves=[])
    await maybe_flag_cheat(session, game, user.id, assessment)
    await session.commit()
    state = state_from_game(game)
    await redis_bus.publish(f"game:{game.id}", {"type": "state", "state": state.model_dump()})
    return state

@router.post("/{game_id}/chat")
async def send_chat(game_id: str, payload: ChatRequest, session: AsyncSession = Depends(db_session), user: User = Depends(get_current_user)):
    game = (await session.execute(select(Game).where(Game.id == game_id))).scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    msg = ChatMessage(game_id=game.id, sender_id=user.id, content=payload.content, is_system=False)
    session.add(msg)
    session.add(AuditEvent(actor_user_id=user.id, game_id=game.id, event_type="chat_message", severity="info", payload={"content": payload.content[:80]}))
    await session.commit()
    return {"ok": True}

@router.post("/{game_id}/rematch", response_model=GameSummary)
async def rematch(game_id: str, session: AsyncSession = Depends(db_session), user: User = Depends(get_current_user)):
    game = (await session.execute(select(Game).where(Game.id == game_id))).scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    code = token_urlsafe(8).replace("-", "").replace("_", "")[:12]
    new_game = Game(
        invite_code=code,
        creator_id=user.id,
        white_id=game.black_id,
        black_id=game.white_id,
        status=GameStatus.waiting,
        time_control_seconds=game.time_control_seconds,
        increment_seconds=game.increment_seconds,
        white_clock_ms=game.time_control_seconds * 1000,
        black_clock_ms=game.time_control_seconds * 1000,
        game_metadata={"rematch_of": game.id},
    )
    session.add(new_game)
    await session.commit()
    return to_summary(new_game)

@router.get("/{game_id}/analysis", response_model=AnalysisResponse)
async def analysis(game_id: str, session: AsyncSession = Depends(db_session), user: User = Depends(get_current_user)):
    game = (await session.execute(select(Game).where(Game.id == game_id))).scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    result = stockfish_service.analyse(game.current_fen, depth=12)
    moves = (await session.execute(select(Move).where(Move.game_id == game.id).order_by(Move.ply.asc()))).scalars().all()
    assessment = evaluate_cheat_risk(game, moves, engine_best_moves=result.principal_variation[:10])
    return AnalysisResponse(game_id=game.id, evaluation_cp=result.evaluation_cp, best_move=result.best_move, principal_variation=result.principal_variation, cheat_score=assessment.score, cheat_reason=assessment.reason)
