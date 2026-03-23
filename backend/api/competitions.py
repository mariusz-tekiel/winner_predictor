from fastapi import APIRouter
from services.source_router import get_all_competitions

router = APIRouter(prefix="/api/competitions", tags=["competitions"])


@router.get("")
async def list_competitions():
    return {"competitions": get_all_competitions()}
