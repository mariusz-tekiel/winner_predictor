"""
Tennis API endpoints — all under /api/tennis/
"""
import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

import tennis.model_store as store
import tennis.trainer as trainer
import tennis.live_api as live_api
import tennis.csv_loader as csv_loader
from tennis.predictor import predict_match
from tennis.constants import TOURS

router = APIRouter(prefix="/api/tennis", tags=["tennis"])


# ── Tours ──────────────────────────────────────────────────────────────────────

@router.get("/tours")
async def get_tours():
    return {"tours": TOURS}


# ── CSV status ────────────────────────────────────────────────────────────────

@router.get("/csv/status")
async def get_csv_status():
    return csv_loader.csv_status()


# ── Upcoming matches ──────────────────────────────────────────────────────────

@router.get("/matches/upcoming")
async def get_upcoming_matches(
    tour: str | None = Query(default=None, description="atp | wta | challenger"),
    surface: str | None = Query(default=None, description="clay | hard | grass"),
):
    matches = await live_api.get_upcoming_matches(tour)
    if surface:
        matches = [m for m in matches if m["surface"] == surface]
    return {"matches": matches}


# ── Predict match ─────────────────────────────────────────────────────────────

@router.get("/matches/{match_id}/predict")
async def predict_tennis_match(
    match_id: str,
    tour: str | None = Query(default=None),
    surface: str | None = Query(default=None),
    odds_1: float | None = Query(default=None, description="Decimal odds for player 1"),
    odds_2: float | None = Query(default=None, description="Decimal odds for player 2"),
    player_1_name: str | None = Query(default=None),
    player_2_name: str | None = Query(default=None),
    player_1_rank: int | None = Query(default=None),
    player_2_rank: int | None = Query(default=None),
    round: str | None = Query(default="R32"),
    tourney_name: str | None = Query(default=""),
):
    if not store.is_trained():
        raise HTTPException(status_code=400, detail="Model nie jest wytrenowany.")

    # Build match dict — try to find from live API first, fallback to query params
    all_matches = await live_api.get_upcoming_matches(tour)
    match = next((m for m in all_matches if m["match_id"] == match_id), None)

    if match is None:
        # Fallback: build from query params
        if not player_1_name or not player_2_name:
            raise HTTPException(
                status_code=404,
                detail="Mecz nie znaleziony. Podaj player_1_name i player_2_name jako parametry.",
            )
        match = {
            "match_id": match_id,
            "tour": tour or "atp",
            "surface": surface or "hard",
            "round": round or "R32",
            "tourney_name": tourney_name or "",
            "player_1": {"id": match_id + "_p1", "name": player_1_name, "rank": player_1_rank},
            "player_2": {"id": match_id + "_p2", "name": player_2_name, "rank": player_2_rank},
            "odds_1": odds_1,
            "odds_2": odds_2,
        }
    else:
        # Override odds if provided
        if odds_1 is not None:
            match["odds_1"] = odds_1
        if odds_2 is not None:
            match["odds_2"] = odds_2

    try:
        result = await predict_match(match)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result


# ── Model training ────────────────────────────────────────────────────────────

@router.post("/model/train")
async def start_training(
    background_tasks: BackgroundTasks,
    tour: str = Query(default="atp", description="atp | wta | challenger"),
    years: str = Query(
        default="2019,2020,2021,2022,2023,2024",
        description="Comma-separated list of years, e.g. 2019,2020,2021",
    ),
):
    year_list = [int(y.strip()) for y in years.split(",") if y.strip().isdigit()]
    if not year_list:
        raise HTTPException(status_code=400, detail="Nieprawidłowe lata.")

    task_id = str(uuid.uuid4())
    background_tasks.add_task(trainer.train_async, tour, year_list, task_id)
    return {"taskId": task_id, "status": "started"}


@router.get("/model/train/{task_id}")
async def get_train_progress(task_id: str):
    return trainer.get_progress(task_id)


@router.get("/model/status")
async def get_model_status():
    meta = store.get_metadata()
    if not meta:
        return {"trained": False}
    return {
        "trained": True,
        "tour": meta.get("tour"),
        "years": meta.get("years"),
        "trained_at": meta.get("trained_at"),
        "sample_count": meta.get("sample_count"),
        "accuracy": meta.get("accuracy"),
        "log_loss": meta.get("log_loss"),
        "brier_score": meta.get("brier_score"),
        "feature_cols": meta.get("feature_cols"),
    }
