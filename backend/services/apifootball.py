"""
API-Football (api-sports.io) client.
Normalizuje dane do tego samego formatu co football-data.org,
dzięki czemu reszta kodu (ML, feature engineering) działa bez zmian.

Rejestracja: https://dashboard.api-football.com/register
Free tier: 100 req/dzień, 10 req/min
"""
import asyncio
import time
from datetime import date
import httpx
from app.config import settings
from services.cache import cache_get, cache_set

BASE_URL = "https://v3.football.api-sports.io"


def _current_season(league_type: str = "european") -> int:
    """
    API-Football free plan: dostęp tylko do sezonów 2022–2024.
    Zwraca 2024 jako najnowszy dostępny sezon.
    """
    return 2024


# competition_code → {league_id, name, league_type}
AF_COMPETITIONS: dict[str, dict] = {
    # API-Football free plan: dostęp tylko do sezonów 2022-2024 (bez bieżącego)
    # Ekstraklasa dostępna tylko na płatnym planie
}

TTL_MATCHES   = 900    # 15 min
TTL_STANDINGS = 3600   # 1h
TTL_H2H       = 3600   # 1h

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

    headers = {
        "x-apisports-key": settings.apifootball_api_key,
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers, params=params or {})

    if resp.status_code == 429:
        await asyncio.sleep(60)
        return await _rate_limited_get(url, params)

    resp.raise_for_status()
    data = resp.json()

    # api-sports.io zwraca błędy w polu "errors" z HTTP 200
    errors = data.get("errors", {})
    if errors:
        raise ValueError(f"API-Football błąd: {errors}")

    return data


async def _fetch(endpoint: str, params: dict = None, ttl: int = 3600) -> dict:
    url = f"{BASE_URL}/{endpoint}"
    cache_key = f"af_{url}" + str(sorted((params or {}).items()))

    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    data = await _rate_limited_get(url, params)
    await cache_set(cache_key, data, ttl)
    return data


# ──────────────────────────────────────────────
# Normalizacja do formatu football-data.org
# ──────────────────────────────────────────────

_STATUS_MAP = {
    "NS":   "SCHEDULED",
    "TBD":  "SCHEDULED",
    "FT":   "FINISHED",
    "AET":  "FINISHED",
    "PEN":  "FINISHED",
    "PST":  "POSTPONED",
    "CANC": "CANCELLED",
    "1H":   "IN_PLAY",
    "HT":   "IN_PLAY",
    "2H":   "IN_PLAY",
    "ET":   "IN_PLAY",
    "P":    "IN_PLAY",
}


def _normalize_fixture(f: dict) -> dict:
    fix   = f["fixture"]
    teams = f["teams"]
    score = f.get("score", {})
    ft    = (score.get("fulltime") or {})

    round_str = f.get("league", {}).get("round", "")
    matchday = None
    if " - " in round_str:
        try:
            matchday = int(round_str.split(" - ")[-1])
        except ValueError:
            pass

    return {
        "id":       fix["id"],
        "utcDate":  fix["date"],
        "status":   _STATUS_MAP.get(fix["status"]["short"], "UNKNOWN"),
        "matchday": matchday,
        "homeTeam": {
            "id":        teams["home"]["id"],
            "name":      teams["home"]["name"],
            "shortName": teams["home"]["name"],
            "crest":     teams["home"].get("logo", ""),
        },
        "awayTeam": {
            "id":        teams["away"]["id"],
            "name":      teams["away"]["name"],
            "shortName": teams["away"]["name"],
            "crest":     teams["away"].get("logo", ""),
        },
        "score": {
            "fullTime": {
                "home": ft.get("home"),
                "away": ft.get("away"),
            }
        },
    }


def _normalize_standings(response: dict) -> dict:
    try:
        league_data = response["response"][0]["league"]
        table       = league_data["standings"][0]
    except (KeyError, IndexError, TypeError):
        return {"standings": []}

    normalized = [
        {
            "position":       entry["rank"],
            "team":           {"id": entry["team"]["id"]},
            "points":         entry["points"],
            "goalDifference": entry["goalsDiff"],
        }
        for entry in table
    ]
    return {"standings": [{"type": "TOTAL", "table": normalized}]}


# ──────────────────────────────────────────────
# Publiczne funkcje API
# ──────────────────────────────────────────────

def _league_id(competition_code: str) -> int:
    return AF_COMPETITIONS[competition_code]["league_id"]


def _season(competition_code: str, season: int = None) -> int:
    if season:
        return season
    league_type = AF_COMPETITIONS[competition_code].get("league_type", "european")
    return _current_season(league_type)


async def get_all_matches(competition_code: str, season: int = None) -> dict:
    data = await _fetch(
        "fixtures",
        {"league": _league_id(competition_code), "season": _season(competition_code, season)},
        TTL_MATCHES,
    )
    matches = [_normalize_fixture(f) for f in data.get("response", [])]
    return {"matches": matches}


async def get_standings(competition_code: str) -> dict:
    data = await _fetch(
        "standings",
        {"league": _league_id(competition_code), "season": _season(competition_code)},
        TTL_STANDINGS,
    )
    return _normalize_standings(data)


async def get_match(match_id: int) -> dict:
    data = await _fetch("fixtures", {"id": match_id}, TTL_MATCHES)
    fixtures = data.get("response", [])
    if not fixtures:
        raise ValueError(f"Mecz {match_id} nie znaleziony w API-Football")
    return _normalize_fixture(fixtures[0])


async def get_head2head(home_team_id: int, away_team_id: int, limit: int = 10) -> dict:
    data = await _fetch(
        "fixtures/headtohead",
        {"h2h": f"{home_team_id}-{away_team_id}", "last": limit},
        TTL_H2H,
    )
    matches = [_normalize_fixture(f) for f in data.get("response", [])]
    return {"matches": matches}
