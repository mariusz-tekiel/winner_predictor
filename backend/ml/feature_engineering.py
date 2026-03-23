"""
Pure feature engineering functions — no I/O, no side effects.
All inputs are plain Python dicts (already fetched from API / cache).
"""
from datetime import datetime, timezone


FEATURE_COLS = [
    "home_form_points",
    "home_form_gf",
    "home_form_ga",
    "home_form_gd",
    "away_form_points",
    "away_form_gf",
    "away_form_ga",
    "away_form_gd",
    "home_position",
    "away_position",
    "position_diff",
    "home_season_points",
    "away_season_points",
    "h2h_home_wins",
    "h2h_draws",
    "h2h_away_wins",
    "h2h_home_win_rate",
    "matchday",
]


def _parse_date(date_str: str) -> datetime:
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))


def _match_result_for_team(match: dict, team_id: int) -> tuple[str, int, int] | None:
    """Return (result, gf, ga) from team's perspective. result in W/D/L."""
    score = match.get("score", {})
    ft = score.get("fullTime", {})
    if not ft or ft.get("home") is None or ft.get("away") is None:
        return None

    home_id = match["homeTeam"]["id"]
    away_id = match["awayTeam"]["id"]

    if home_id != team_id and away_id != team_id:
        return None

    hg, ag = ft["home"], ft["away"]
    is_home = home_id == team_id
    gf = hg if is_home else ag
    ga = ag if is_home else hg

    if hg > ag:
        result = "W" if is_home else "L"
    elif hg < ag:
        result = "L" if is_home else "W"
    else:
        result = "D"

    return result, gf, ga


def compute_form(all_matches: list[dict], team_id: int, before_date: str, n: int = 5) -> dict:
    """Compute form metrics for a team from finished matches before a given date."""
    cutoff = _parse_date(before_date)

    relevant = []
    for m in all_matches:
        if m.get("status") != "FINISHED":
            continue
        match_date = _parse_date(m["utcDate"])
        if match_date >= cutoff:
            continue
        r = _match_result_for_team(m, team_id)
        if r is None:
            continue
        relevant.append((match_date, r))

    relevant.sort(key=lambda x: x[0], reverse=True)
    recent = [r for _, r in relevant[:n]]

    if not recent:
        return {"form_points": 0, "gf": 0, "ga": 0, "gd": 0}

    points = sum(3 if r == "W" else (1 if r == "D" else 0) for r, _, _ in recent)
    gf = sum(g for _, g, _ in recent)
    ga = sum(g for _, _, g in recent)

    return {"form_points": points, "gf": gf, "ga": ga, "gd": gf - ga}


def compute_standings_map(standings_data: dict) -> dict[int, dict]:
    """Build team_id -> {position, points, gd} map."""
    result = {}
    if not standings_data or "standings" not in standings_data:
        return result

    for table in standings_data["standings"]:
        if table.get("type") == "TOTAL":
            for entry in table["table"]:
                tid = entry["team"]["id"]
                result[tid] = {
                    "position": entry.get("position", 20),
                    "points": entry.get("points", 0),
                    "gd": entry.get("goalDifference", 0),
                }
    return result


def compute_h2h(h2h_data: dict, home_team_id: int) -> dict:
    """Compute H2H stats from /matches/{id}/head2head response."""
    matches = h2h_data.get("matches", [])

    home_wins = draws = away_wins = 0
    for m in matches:
        score = m.get("score", {})
        ft = score.get("fullTime", {})
        if not ft or ft.get("home") is None:
            continue

        hg, ag = ft["home"], ft["away"]
        mh_id = m["homeTeam"]["id"]

        if hg > ag:
            winner_id = mh_id
        elif ag > hg:
            winner_id = m["awayTeam"]["id"]
        else:
            winner_id = None

        if winner_id is None:
            draws += 1
        elif winner_id == home_team_id:
            home_wins += 1
        else:
            away_wins += 1

    total = home_wins + draws + away_wins
    home_win_rate = home_wins / total if total > 0 else 0.33

    return {
        "h2h_home_wins": home_wins,
        "h2h_draws": draws,
        "h2h_away_wins": away_wins,
        "h2h_home_win_rate": round(home_win_rate, 3),
    }


def build_feature_vector(
    home_form: dict,
    away_form: dict,
    standings_map: dict,
    h2h: dict,
    home_team_id: int,
    away_team_id: int,
    matchday: int,
) -> list[float]:
    """Assemble ordered feature vector matching FEATURE_COLS."""
    home_standing = standings_map.get(home_team_id, {"position": 12, "points": 0})
    away_standing = standings_map.get(away_team_id, {"position": 12, "points": 0})

    home_pos = home_standing["position"]
    away_pos = away_standing["position"]

    return [
        home_form["form_points"],
        home_form["gf"],
        home_form["ga"],
        home_form["gd"],
        away_form["form_points"],
        away_form["gf"],
        away_form["ga"],
        away_form["gd"],
        home_pos,
        away_pos,
        away_pos - home_pos,
        home_standing["points"],
        away_standing["points"],
        h2h["h2h_home_wins"],
        h2h["h2h_draws"],
        h2h["h2h_away_wins"],
        h2h["h2h_home_win_rate"],
        matchday or 1,
    ]


def get_match_outcome(match: dict) -> str | None:
    """Return '1', 'X', or '2' for a finished match."""
    score = match.get("score", {})
    ft = score.get("fullTime", {})
    if not ft or ft.get("home") is None or ft.get("away") is None:
        return None
    hg, ag = ft["home"], ft["away"]
    if hg > ag:
        return "1"
    if ag > hg:
        return "2"
    return "X"
