import asyncio
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from ml.trainer import train_async, get_progress
import ml.model_store as store
from services.football_api import COMPETITIONS as FD_COMPETITIONS
from services.apifootball import AF_COMPETITIONS

ALL_COMPETITIONS = {**FD_COMPETITIONS, **{k: v["name"] for k, v in AF_COMPETITIONS.items()}}

router = APIRouter(prefix="/api/model", tags=["model"])


@router.post("/train")
async def train_model(
    background_tasks: BackgroundTasks,
    competition: str = Query(...),
    seasons: str = Query("", description="Comma-separated seasons, e.g. 2022,2023"),
):
    if competition not in ALL_COMPETITIONS:
        raise HTTPException(404, f"Liga '{competition}' nie istnieje.")

    season_list = []
    if seasons:
        try:
            season_list = [int(s.strip()) for s in seasons.split(",") if s.strip()]
        except ValueError:
            raise HTTPException(400, "Nieprawidłowy format sezonów.")

    task_id = str(uuid.uuid4())

    async def run():
        await train_async(competition, season_list, task_id)

    background_tasks.add_task(run)

    return {"taskId": task_id, "status": "queued"}


@router.get("/train/{task_id}")
async def get_train_status(task_id: str):
    progress = get_progress(task_id)
    if progress["status"] == "not_found":
        raise HTTPException(404, "Task nie znaleziony.")
    return progress


@router.get("/status")
async def model_status():
    meta = store.get_metadata()
    if meta is None:
        return {"trained": False}

    return {
        "trained": True,
        "trainedAt": meta.get("trained_at"),
        "accuracy": meta.get("accuracy"),
        "sampleCount": meta.get("sample_count"),
        "competition": meta.get("competition"),
    }
