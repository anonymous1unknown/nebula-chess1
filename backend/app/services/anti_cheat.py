from __future__ import annotations
from dataclasses import dataclass
from statistics import mean
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Move, CheatFlag, CheatStatus, Game

@dataclass
class CheatAssessment:
    score: float
    reason: str
    evidence: dict[str, Any]

def evaluate_cheat_risk(game: Game, moves: list[Move], engine_best_moves: list[str] | None = None) -> CheatAssessment:
    if not moves:
        return CheatAssessment(0.0, "no moves", {})
    durations = [m.duration_ms for m in moves if m.duration_ms is not None]
    avg_duration = mean(durations) if durations else None
    engine_matches = 0
    if engine_best_moves:
        for m, best in zip(moves[-len(engine_best_moves):], engine_best_moves):
            if m.uci == best:
                engine_matches += 1
    match_rate = engine_matches / max(1, len(engine_best_moves or []))
    score = 0.0
    if avg_duration is not None and avg_duration < 900:
        score += 0.2
    if match_rate >= 0.75:
        score += 0.55
    if len(moves) >= 20 and match_rate >= 0.65:
        score += 0.2
    reason = "engine-like move correlation" if score >= 0.5 else "within normal bounds"
    evidence = {"avg_duration_ms": avg_duration, "match_rate": match_rate, "moves_considered": len(moves)}
    return CheatAssessment(score, reason, evidence)

async def maybe_flag_cheat(session: AsyncSession, game: Game, user_id: str | None, assessment: CheatAssessment) -> CheatFlag | None:
    if assessment.score < 0.5:
        return None
    flag = CheatFlag(
        game_id=game.id,
        user_id=user_id,
        score=assessment.score,
        status=CheatStatus.needs_review,
        reason=assessment.reason,
        evidence=assessment.evidence,
    )
    session.add(flag)
    await session.flush()
    return flag
