from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import ml.model_store as store
from api import competitions, matches, model as model_router
from services.cache import cache_clear_expired


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load model into memory if it exists
    store.load()
    await cache_clear_expired()
    yield


app = FastAPI(
    title="Winner Predictor API",
    description="Predykcja wyników meczów piłkarskich (1/X/2)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(competitions.router)
app.include_router(matches.router)
app.include_router(model_router.router)


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "modelLoaded": store.is_trained(),
    }


@app.get("/api/debug/af")
async def debug_apifootball():
    """Testuje połączenie z API-Football i zwraca surową odpowiedź."""
    import httpx
    from app.config import settings
    key = settings.apifootball_api_key
    headers = {"x-apisports-key": key, "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://v3.football.api-sports.io/status",
            headers=headers,
        )
    return {
        "http_status": resp.status_code,
        "key_used": key[:6] + "***" if key else "(brak)",
        "response": resp.json(),
    }
