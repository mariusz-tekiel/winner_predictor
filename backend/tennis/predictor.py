"""
Assembles features for a live match and returns probability + value signal.
"""
import difflib
import numpy as np
import pandas as pd
from datetime import datetime, timezone

import tennis.model_store as store
import tennis.csv_loader as loader
from tennis.feature_engineering import (
    compute_player_stats,
    compute_h2h,
    build_feature_vector,
)
from tennis.constants import VALUE_THRESHOLD

# In-memory name → id map, built once per session
_name_to_id: dict[str, str] = {}
_name_map_tour: str | None = None


def _build_name_map(df: pd.DataFrame, tour: str):
    global _name_to_id, _name_map_tour
    if _name_map_tour == tour and _name_to_id:
        return
    mapping = {}
    for _, row in df[["winner_id", "winner_name"]].drop_duplicates().iterrows():
        mapping[str(row["winner_name"]).lower()] = str(row["winner_id"])
    for _, row in df[["loser_id", "loser_name"]].drop_duplicates().iterrows():
        mapping[str(row["loser_name"]).lower()] = str(row["loser_id"])
    _name_to_id = mapping
    _name_map_tour = tour


def _resolve_id(name: str, api_id: str) -> str:
    """Try to find CSV player_id by name fuzzy match, fallback to api_id."""
    if not _name_to_id:
        return api_id
    key = name.lower()
    if key in _name_to_id:
        return _name_to_id[key]
    matches = difflib.get_close_matches(key, _name_to_id.keys(), n=1, cutoff=0.75)
    if matches:
        return _name_to_id[matches[0]]
    return api_id


def _compute_value_signal(
    model_prob_1: float,
    model_prob_2: float,
    odds_1: float | None,
    odds_2: float | None,
) -> dict:
    result = {
        "p1_edge": None,
        "p2_edge": None,
        "recommendation": "SKIP",
        "reason": "no_odds",
    }

    if odds_1 and odds_1 > 1.0:
        implied_1 = 1.0 / odds_1
        result["p1_edge"] = round(model_prob_1 - implied_1, 4)

    if odds_2 and odds_2 > 1.0:
        implied_2 = 1.0 / odds_2
        result["p2_edge"] = round(model_prob_2 - implied_2, 4)

    if result["p1_edge"] is not None and result["p1_edge"] > VALUE_THRESHOLD:
        result["recommendation"] = "BET_P1"
        result["reason"] = f"edge={result['p1_edge']:.1%}"
    elif result["p2_edge"] is not None and result["p2_edge"] > VALUE_THRESHOLD:
        result["recommendation"] = "BET_P2"
        result["reason"] = f"edge={result['p2_edge']:.1%}"
    else:
        result["recommendation"] = "SKIP"
        result["reason"] = "no_value_edge" if (result["p1_edge"] is not None or result["p2_edge"] is not None) else "no_odds"

    return result


async def predict_match(match: dict) -> dict:
    """
    match: normalized dict from live_api._norm_match().
    Returns prediction + value signal.
    """
    model = store.load()
    if model is None:
        raise ValueError("Model nie jest wytrenowany. Wytrenuj model najpierw.")

    meta = store.get_metadata()
    tour = match.get("tour", meta.get("tour", "atp") if meta else "atp")

    # Load recent CSV data for feature computation (last 3 years)
    now = pd.Timestamp(datetime.now(timezone.utc).replace(tzinfo=None))
    years = list(range(now.year - 3, now.year + 1))
    df = loader.load_matches_df(tour, years)

    if not df.empty:
        _build_name_map(df, tour)

    p1 = match["player_1"]
    p2 = match["player_2"]
    surface = match.get("surface", "hard")
    round_str = match.get("round", "R32")
    best_of = 5 if "Grand Slam" in match.get("tourney_name", "") else 3

    p1_id = _resolve_id(p1["name"], p1["id"])
    p2_id = _resolve_id(p2["name"], p2["id"])

    p1_rank = p1.get("rank") or 300
    p2_rank = p2.get("rank") or 300
    p1_pts = 0
    p2_pts = 0

    # Try to get rank points from CSV
    if not df.empty:
        w = df[df["winner_id"].astype(str) == p1_id].tail(1)
        if not w.empty:
            p1_pts = int(w.iloc[0].get("winner_rank_points") or 0)
        l = df[df["loser_id"].astype(str) == p1_id].tail(1)
        if not l.empty and p1_pts == 0:
            p1_pts = int(l.iloc[0].get("loser_rank_points") or 0)

        w2 = df[df["winner_id"].astype(str) == p2_id].tail(1)
        if not w2.empty:
            p2_pts = int(w2.iloc[0].get("winner_rank_points") or 0)
        l2 = df[df["loser_id"].astype(str) == p2_id].tail(1)
        if not l2.empty and p2_pts == 0:
            p2_pts = int(l2.iloc[0].get("loser_rank_points") or 0)

    p1_stats = compute_player_stats(df, p1_id, surface, now) if not df.empty else _neutral()
    p2_stats = compute_player_stats(df, p2_id, surface, now) if not df.empty else _neutral()
    h2h = compute_h2h(df, p1_id, p2_id, surface, now) if not df.empty else _neutral_h2h()

    fv = build_feature_vector(
        p1_stats, p2_stats, h2h,
        p1_rank, p2_rank, p1_pts, p2_pts,
        best_of == 5, round_str,
    )
    X = np.array([fv])

    proba = model.predict_proba(X)[0]
    # classes_ order may be [0, 1]
    classes = list(model.classes_) if hasattr(model, "classes_") else [0, 1]
    idx1 = classes.index(1) if 1 in classes else 1
    p1_win_prob = float(proba[idx1])
    p2_win_prob = 1.0 - p1_win_prob

    signal = _compute_value_signal(
        p1_win_prob, p2_win_prob,
        match.get("odds_1"), match.get("odds_2"),
    )

    return {
        "player_1_win_prob": round(p1_win_prob * 100, 1),
        "player_2_win_prob": round(p2_win_prob * 100, 1),
        "signal": signal,
        "insights": {
            "p1_surface_winrate": round(p1_stats["surface_winrate"] * 100, 1),
            "p2_surface_winrate": round(p2_stats["surface_winrate"] * 100, 1),
            "p1_form5": round(p1_stats["form5_winrate"] * 100, 1),
            "p2_form5": round(p2_stats["form5_winrate"] * 100, 1),
            "p1_fatigue": {
                "matches_last7": p1_stats["matches_last7"],
                "back_to_back": bool(p1_stats["back_to_back"]),
            },
            "p2_fatigue": {
                "matches_last7": p2_stats["matches_last7"],
                "back_to_back": bool(p2_stats["back_to_back"]),
            },
            "h2h": {
                "p1_wins": h2h["h2h_p1_wins"],
                "p2_wins": h2h["h2h_p2_wins"],
                "total": h2h["h2h_total"],
            },
        },
    }


def _neutral():
    from tennis.feature_engineering import _neutral_player_stats
    return _neutral_player_stats()


def _neutral_h2h():
    return {"h2h_p1_wins": 0, "h2h_p2_wins": 0, "h2h_total": 0, "h2h_p1_winrate": 0.5}
