"""
Routing do właściwego API na podstawie kodu ligi.
Obie strony zwracają ujednolicony format (football-data.org schema).
"""
import services.football_api as fd
import services.apifootball as af
from services.apifootball import AF_COMPETITIONS
from services.football_api import COMPETITIONS as FD_COMPETITIONS


def get_source(competition_code: str) -> str:
    if competition_code in AF_COMPETITIONS:
        return "api-football"
    return "football-data"


def get_all_competitions() -> list[dict]:
    result = []
    for code, name in FD_COMPETITIONS.items():
        result.append({"code": code, "name": name, "source": "football-data"})
    for code, info in AF_COMPETITIONS.items():
        result.append({"code": code, "name": info["name"], "source": "api-football"})
    return result


async def get_all_matches(competition_code: str, season: int = None) -> dict:
    if get_source(competition_code) == "api-football":
        return await af.get_all_matches(competition_code, season)
    return await fd.get_all_matches(competition_code, season)


async def get_standings(competition_code: str) -> dict:
    if get_source(competition_code) == "api-football":
        return await af.get_standings(competition_code)
    return await fd.get_standings(competition_code)


async def get_match(match_id: int, competition_code: str) -> dict:
    if get_source(competition_code) == "api-football":
        return await af.get_match(match_id)
    return await fd.get_match(match_id)


async def get_head2head(
    match_id: int,
    home_team_id: int,
    away_team_id: int,
    competition_code: str,
) -> dict:
    if get_source(competition_code) == "api-football":
        return await af.get_head2head(home_team_id, away_team_id)
    return await fd.get_head2head(match_id)


async def get_upcoming_matches(competition_code: str) -> list[dict]:
    """Zwraca listę zaplanowanych meczów niezależnie od źródła."""
    if get_source(competition_code) == "api-football":
        data = await af.get_all_matches(competition_code)
        all_matches = data.get("matches", [])
        upcoming = [m for m in all_matches if m.get("status") in ("SCHEDULED", "TIMED")]
    else:
        data1 = await fd.get_matches(competition_code, status="SCHEDULED")
        data2 = await fd.get_matches(competition_code, status="TIMED")
        upcoming = data1.get("matches", []) + data2.get("matches", [])

    upcoming.sort(key=lambda m: m["utcDate"])
    return upcoming[:30]
