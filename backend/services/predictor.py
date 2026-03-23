import asyncio
import numpy as np
import ml.model_store as store
import services.source_router as router_svc
from ml.feature_engineering import (
    compute_form,
    compute_standings_map,
    compute_h2h,
    build_feature_vector,
)


async def predict_match(competition_code: str, match_id: int) -> dict:
    model = store.load()
    if model is None:
        raise ValueError("Model nie jest jeszcze wytrenowany. Kliknij 'Trenuj model' najpierw.")

    # Pobierz mecz i dane ligi równolegle
    match, all_matches_data, standings_data = await asyncio.gather(
        router_svc.get_match(match_id, competition_code),
        router_svc.get_all_matches(competition_code),
        router_svc.get_standings(competition_code),
    )

    all_matches = all_matches_data.get("matches", [])
    home_id   = match["homeTeam"]["id"]
    away_id   = match["awayTeam"]["id"]
    match_date = match["utcDate"]
    matchday   = match.get("matchday", 1) or 1

    home_form = compute_form(all_matches, home_id, match_date)
    away_form = compute_form(all_matches, away_id, match_date)

    standings_map = compute_standings_map(standings_data)

    # H2H — pobierz z właściwego API
    h2h_data = await router_svc.get_head2head(match_id, home_id, away_id, competition_code)
    h2h = compute_h2h(h2h_data, home_id)

    fv = build_feature_vector(
        home_form, away_form, standings_map, h2h,
        home_id, away_id, matchday,
    )

    X = np.array([fv], dtype=float)
    classes = model.classes_
    proba   = model.predict_proba(X)[0]
    prediction = classes[int(np.argmax(proba))]

    proba_map = {c: round(float(p) * 100, 1) for c, p in zip(classes, proba)}
    for key in ("1", "X", "2"):
        proba_map.setdefault(key, 0.0)

    home_standing = standings_map.get(home_id, {})
    away_standing = standings_map.get(away_id, {})

    return {
        "prediction": prediction,
        "probabilities": {
            "home": proba_map.get("1", 0),
            "draw": proba_map.get("X", 0),
            "away": proba_map.get("2", 0),
        },
        "confidence": round(float(max(proba)) * 100, 1),
        "insights": {
            "homeForm": {
                "points":        home_form["form_points"],
                "goalsScored":   home_form["gf"],
                "goalsConceded": home_form["ga"],
            },
            "awayForm": {
                "points":        away_form["form_points"],
                "goalsScored":   away_form["gf"],
                "goalsConceded": away_form["ga"],
            },
            "homePosition": home_standing.get("position", "—"),
            "awayPosition": away_standing.get("position", "—"),
            "h2h": {
                "homeWins": h2h["h2h_home_wins"],
                "draws":    h2h["h2h_draws"],
                "awayWins": h2h["h2h_away_wins"],
            },
        },
    }
