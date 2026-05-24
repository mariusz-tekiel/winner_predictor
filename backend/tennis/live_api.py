"""
API-Tennis client for upcoming matches and current rankings.
Endpoint: https://api.api-tennis.com/tennis/
Rate limit: handled via asyncio.Semaphore (same pattern as football_api.py)
"""
import asyncio
import httpx
from app.config import settings
from services.cache import cache_get, cache_set
from tennis.constants import SURFACE_NORM

_BASE_URL = "https://api.api-tennis.com/tennis/"
_SEMAPHORE = asyncio.Semaphore(3)  # max 3 concurrent requests

TTL_MATCHES = 900    # 15 min
TTL_RANKINGS = 3600  # 1h


def _headers() -> dict:
    return {"Accept": "application/json"}


def _params(extra: dict) -> dict:
    return {"APIkey": settings.tennis_api_key, **extra}


async def _get(method: str, extra_params: dict) -> dict:
    url = _BASE_URL
    params = _params({"method": method, **extra_params})
    cache_key = f"tennis:{method}:{sorted(extra_params.items())}"

    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    async with _SEMAPHORE:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params, headers=_headers())
            resp.raise_for_status()
            data = resp.json()

    await cache_set(cache_key, data, ttl_seconds=TTL_MATCHES)
    return data


def _norm_surface(raw: str | None) -> str:
    if not raw:
        return "hard"
    return SURFACE_NORM.get(raw.strip().capitalize(), "hard")


def _norm_match(raw: dict) -> dict:
    """Normalize API-Tennis match dict to internal schema."""
    return {
        "match_id": str(raw.get("event_key", "")),
        "match_date": raw.get("event_date", "") + "T" + raw.get("event_time", "00:00") + ":00",
        "tour": _detect_tour(raw.get("league_name", "")),
        "surface": _norm_surface(raw.get("court_surface")),
        "tourney_name": raw.get("league_name", ""),
        "round": raw.get("event_round", ""),
        "player_1": {
            "id": str(raw.get("event_home_team_id", "")),
            "name": raw.get("event_home_team", ""),
            "rank": _safe_int(raw.get("home_player_rank")),
        },
        "player_2": {
            "id": str(raw.get("event_away_team_id", "")),
            "name": raw.get("event_away_team", ""),
            "rank": _safe_int(raw.get("away_player_rank")),
        },
        "odds_1": _safe_float(raw.get("odd_1")),
        "odds_2": _safe_float(raw.get("odd_2")),
    }


def _detect_tour(league_name: str) -> str:
    name = league_name.lower()
    if "wta" in name or "women" in name:
        return "wta"
    if "challenger" in name or "itf" in name:
        return "challenger"
    return "atp"


def _safe_int(val) -> int | None:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _safe_float(val) -> float | None:
    try:
        v = float(val)
        return v if v > 1.0 else None
    except (TypeError, ValueError):
        return None


async def get_upcoming_matches(tour: str | None = None) -> list[dict]:
    """Fetch upcoming/live matches. Optionally filter by tour."""
    try:
        data = await _get("get_events", {"event_type": "Tennis", "event_status": "notstarted"})
    except Exception:
        return []

    matches = []
    for item in data.get("result", []):
        m = _norm_match(item)
        if tour and m["tour"] != tour:
            continue
        matches.append(m)

    return matches


async def get_rankings(tour: str) -> dict[str, int]:
    """Return {player_name: rank} for given tour."""
    method_map = {"atp": "get_standings", "wta": "get_standings"}
    league_map = {"atp": "ATP", "wta": "WTA"}

    try:
        data = await _get(method_map.get(tour, "get_standings"),
                          {"standing_type": league_map.get(tour, "ATP")})
    except Exception:
        return {}

    result = {}
    for entry in data.get("result", []):
        name = entry.get("team_name") or entry.get("player_name", "")
        rank = _safe_int(entry.get("standing_place") or entry.get("rank"))
        if name and rank:
            result[name] = rank
    return result
