from __future__ import annotations
from datetime import datetime, timezone
from io import StringIO
from typing import Any
import chess
import chess.pgn
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Game, Move, GameStatus, AuditEvent, RatingHistory, CheatFlag, CheatStatus

def board_from_game(game: Game) -> chess.Board:
    if game.current_fen and game.current_fen != "startpos":
        return chess.Board(game.current_fen)
    return chess.Board()


def resolve_move(board: chess.Board, uci: str) -> chess.Move:
    try:
        direct = chess.Move.from_uci(uci)
        if direct in board.legal_moves:
            return direct
    except Exception:
        pass

    if len(uci) == 4:
        candidates = [m for m in board.legal_moves if m.uci().startswith(uci)]
        if candidates:
            queens = [m for m in candidates if m.promotion == chess.QUEEN]
            return queens[0] if queens else candidates[0]

    raise ValueError("Illegal move")

def board_snapshot(board: chess.Board) -> dict[str, Any]:
    return {
        "fen": board.fen(),
        "turn": "w" if board.turn == chess.WHITE else "b",
        "is_check": board.is_check(),
        "is_checkmate": board.is_checkmate(),
        "is_stalemate": board.is_stalemate(),
        "is_insufficient_material": board.is_insufficient_material(),
        "legal_moves": [m.uci() for m in board.legal_moves],
    }

def build_pgn(game: Game, moves: list[Move]) -> str:
    board = chess.Board()
    pgn_game = chess.pgn.Game()
    node = pgn_game
    for mv in moves:
        move = board.parse_uci(mv.uci)
        san = board.san(move)
        board.push(move)
        node = node.add_variation(move)
    pgn_game.headers["Event"] = "Nebula Chess"
    pgn_game.headers["Site"] = "Nebula Chess"
    pgn_game.headers["Result"] = game.result or "*"
    exporter = chess.pgn.StringExporter(headers=True, variations=False, comments=False)
    return pgn_game.accept(exporter)

def determine_result(board: chess.Board, white_id: str | None, black_id: str | None) -> tuple[str | None, str | None]:
    if board.is_checkmate():
        winner = black_id if board.turn == chess.WHITE else white_id
        return ("1-0" if winner == white_id else "0-1"), winner
    if board.is_stalemate() or board.is_insufficient_material() or board.is_repetition(3) or board.can_claim_fifty_moves():
        return "1/2-1/2", None
    return None, None


async def maybe_play_ai_move(session: AsyncSession, game: Game) -> tuple[Game | None, Move | None, dict[str, Any] | None]:
    if not isinstance(game.game_metadata, dict) or not game.game_metadata.get("against_ai"):
        return None, None, None
    if game.status == GameStatus.finished:
        return None, None, None
    board = board_from_game(game)
    # AI always plays the side that is not a human player.
    human_ids = {game.white_id, game.black_id} - {None}
    if len(human_ids) == 2:
        return None, None, None
    from app.services.stockfish_service import stockfish_service
    analysis = stockfish_service.analyse(board.fen(), depth=10)
    move_uci = analysis.best_move
    if not move_uci:
        legal = list(board.legal_moves)
        if not legal:
            return None, None, None
        move_uci = legal[0].uci()
    ai_user_id = None
    return await apply_move(session, game, ai_user_id, move_uci, duration_ms=250)

async def apply_move(session: AsyncSession, game: Game, user_id: str | None, uci: str, duration_ms: int | None = None) -> tuple[Game, Move, dict[str, Any]]:
    board = board_from_game(game)
    fen_before = board.fen()
    move = resolve_move(board, uci)
    san = board.san(move)
    board.push(move)
    fen_after = board.fen()

    game.current_fen = fen_after
    game.turn = "w" if board.turn == chess.WHITE else "b"
    game.move_count += 1
    game.last_move_at = datetime.now(timezone.utc)

    if game.white_clock_ms is not None and game.black_clock_ms is not None:
        if board.turn == chess.BLACK:
            game.white_clock_ms = max(0, game.white_clock_ms - int(duration_ms or 0))
        else:
            game.black_clock_ms = max(0, game.black_clock_ms - int(duration_ms or 0))

    result, winner = determine_result(board, game.white_id, game.black_id)
    if result:
        game.result = result
        game.winner_id = winner
        game.status = GameStatus.finished
        game.finished_at = datetime.now(timezone.utc)

    move_row = Move(
        game_id=game.id,
        user_id=user_id,
        ply=game.move_count,
        move_number=(game.move_count + 1) // 2,
        uci=uci,
        san=san,
        fen_before=fen_before,
        fen_after=fen_after,
        duration_ms=duration_ms,
        is_legal=True,
    )
    session.add(move_row)
    session.add(AuditEvent(
        actor_user_id=user_id,
        game_id=game.id,
        event_type="move_made",
        severity="info",
        payload={"uci": uci, "san": san},
    ))
    await session.flush()

    moves = (await session.execute(select(Move).where(Move.game_id == game.id).order_by(Move.ply.asc()))).scalars().all()
    game.pgn = build_pgn(game, moves)

    return game, move_row, {"fen_before": fen_before, "fen_after": fen_after, "san": san, "result": game.result, "winner_id": game.winner_id}
