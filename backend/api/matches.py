from fastapi import APIRouter, HTTPException, Query
from services import source_router as router_svc
from services.predictor import predict_match
from services.apifootball import AF_COMPETITIONS
from services.football_api import COMPETITIONS as FD_COMPETITIONS

router = APIRouter(prefix="/api/matches", tags=["matches"])

ALL_COMPETITIONS = {**FD_COMPETITIONS, **{k: v["name"] for k, v in AF_COMPETITIONS.items()}}


@router.get("/upcoming")
async def get_upcoming_matches(
    competition: str = Query(..., description="Kod ligi, np. PL lub EKSA"),
):
    if competition not in ALL_COMPETITIONS:
        raise HTTPException(404, f"Liga '{competition}' nie istnieje.")

    try:
        matches = await router_svc.get_upcoming_matches(competition)
    except Exception as e:
        raise HTTPException(500, f"Błąd pobierania meczów: {str(e)}")

    return {"matches": matches, "competition": competition}


@router.get("/{match_id}/predict")
async def get_prediction(
    match_id: int,
    competition: str = Query(..., description="Kod ligi, np. PL lub EKSA"),
):
    if competition not in ALL_COMPETITIONS:
        raise HTTPException(404, f"Liga '{competition}' nie istnieje.")

    try:
        result = await predict_match(competition, match_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Błąd predykcji: {str(e)}")

    return result
