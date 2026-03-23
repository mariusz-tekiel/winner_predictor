import asyncio
import time
import httpx
from app.config import settings
from services.cache import cache_get, cache_set

BASE_URL = "https://api.football-data.org/v4"

COMPETITIONS = {
    # Ligi krajowe
    "PL":  "Premier League (Anglia)",
    "BL1": "Bundesliga (Niemcy)",
    "SA":  "Serie A (Włochy)",
    "PD":  "La Liga (Hiszpania)",
    "FL1": "Ligue 1 (Francja)",
    "DED": "Eredivisie (Holandia)",
    "PPL": "Primeira Liga (Portugalia)",
    "ELC": "Championship (Anglia)",
    "BSA": "Série A (Brazylia)",
    # Rozgrywki europejskie
    "CL":  "Liga Mistrzów UEFA",
}

# TTLs in seconds
TTL_COMPETITIONS = 86400   # 24h
TTL_MATCHES = 900          # 15 min
TTL_STANDINGS = 3600       # 1h
TTL_TEAM_MATCHES = 3600    # 1h
TTL_H2H = 3600             # 1h

_rate_lock = asyncio.Lock()
_request_times: list[float] = []
MAX_CALLS = 9
WINDOW = 60.0


async def _rate_limited_get(url: str, params: dict = None) -> dict:
    global _request_times

    async with _rate_lock:
        now = time.monotonic()
        _request_times = [t for t in _request_times if now - t < WINDOW]

        if len(_request_times) >= MAX_CALLS:
            wait = WINDOW - (now - _request_times[0]) + 0.5
            await asyncio.sleep(wait)
            _request_times = [t for t in _request_times if time.monotonic() - t < WINDOW]

        _request_times.append(time.monotonic())

    headers = {"X-Auth-Token": settings.football_api_key}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers, params=params or {})

    if resp.status_code == 429:
        retry_after = int(resp.headers.get("X-RequestCounter-Reset", 60))
        await asyncio.sleep(retry_after)
        return await _rate_limited_get(url, params)

    resp.raise_for_status()
    return resp.json()


async def _fetch(endpoint: str, params: dict = None, ttl: int = 3600) -> dict:
    url = f"{BASE_URL}/{endpoint}"
    cache_key = url + str(sorted((params or {}).items()))

    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    data = await _rate_limited_get(url, params)
    await cache_set(cache_key, data, ttl)
    return data


async def get_competitions() -> dict:
    return await _fetch("competitions", {"plan": "TIER_ONE"}, TTL_COMPETITIONS)


async def get_matches(competition_code: str, status: str = None, season: int = None) -> dict:
    params = {}
    if status:
        params["status"] = status
    if season:
        params["season"] = season
    return await _fetch(f"competitions/{competition_code}/matches", params, TTL_MATCHES)


async def get_all_matches(competition_code: str, season: int = None) -> dict:
    params = {}
    if season:
        params["season"] = season
    return await _fetch(f"competitions/{competition_code}/matches", params, TTL_MATCHES)


async def get_standings(competition_code: str) -> dict:
    return await _fetch(f"competitions/{competition_code}/standings", {}, TTL_STANDINGS)


async def get_team_matches(team_id: int, limit: int = 10) -> dict:
    return await _fetch(
        f"teams/{team_id}/matches",
        {"status": "FINISHED", "limit": limit},
        TTL_TEAM_MATCHES
    )


async def get_head2head(match_id: int, limit: int = 10) -> dict:
    return await _fetch(f"matches/{match_id}/head2head", {"limit": limit}, TTL_H2H)


async def get_match(match_id: int) -> dict:
    return await _fetch(f"matches/{match_id}", {}, TTL_MATCHES)


def get_available_competitions() -> dict:
    return COMPETITIONS
