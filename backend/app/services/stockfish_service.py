from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any
import chess
import chess.engine
from app.core.config import get_settings

@dataclass
class AnalysisResult:
    evaluation_cp: int | None
    best_move: str | None
    principal_variation: list[str]

class StockfishService:
    def __init__(self) -> None:
        settings = get_settings()
        self.path = os.getenv("STOCKFISH_PATH", settings.stockfish_path)
        self._engine: chess.engine.SimpleEngine | None = None

    def available(self) -> bool:
        return bool(self.path and os.path.exists(self.path))

    def _ensure_engine(self) -> chess.engine.SimpleEngine:
        if self._engine is None:
            self._engine = chess.engine.SimpleEngine.popen_uci(self.path)
        return self._engine

    def analyse(self, fen: str, depth: int = 12) -> AnalysisResult:
        board = chess.Board(fen if fen != "startpos" else None)
        if not self.available():
            return AnalysisResult(None, None, [])
        engine = self._ensure_engine()
        info = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=1)
        score = info["score"].pov(board.turn)
        pv = [m.uci() for m in info.get("pv", [])]
        best = pv[0] if pv else None
        cp = score.score(mate_score=100000)
        return AnalysisResult(cp, best, pv)

    def close(self) -> None:
        if self._engine is not None:
            try:
                self._engine.quit()
            finally:
                self._engine = None

stockfish_service = StockfishService()
