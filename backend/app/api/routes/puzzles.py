from __future__ import annotations
from fastapi import APIRouter, Depends
from app.deps import get_current_user
from app.models import User

router = APIRouter(prefix="/puzzles", tags=["puzzles"])

@router.get("/daily")
async def daily_puzzle(user: User = Depends(get_current_user)):
    return {
        "id": "daily-1",
        "fen": "r1bqkbnr/pppp1ppp/2n5/4p3/1b1P4/5NP1/PPP1PPBP/RNBQK2R w KQkq - 2 4",
        "side_to_move": "w",
        "goal": "Find the strongest move",
    }
