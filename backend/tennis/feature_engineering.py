"""
Pure feature engineering for tennis match prediction.
No I/O — all inputs are DataFrames + scalars.
"""
import numpy as np
import pandas as pd
from tennis.constants import ROUND_ORDER

TENNIS_FEATURE_COLS = [
    # Ranking
    "p1_rank", "p2_rank", "rank_diff",
    "p1_rank_points", "p2_rank_points", "rank_points_ratio",
    # Surface win rate (last 2 years, same surface)
    "p1_surface_winrate", "p2_surface_winrate",
    "p1_surface_matches", "p2_surface_matches",
    # Form last 5 (all surfaces)
    "p1_form5_winrate", "p2_form5_winrate",
    "p1_form5_vs_top50_winrate", "p2_form5_vs_top50_winrate",
    "p1_form5_sets_won_pct", "p2_form5_sets_won_pct",
    # Form last 10
    "p1_form10_winrate", "p2_form10_winrate",
    "p1_form10_sets_won_pct", "p2_form10_sets_won_pct",
    # Fatigue
    "p1_matches_last7", "p2_matches_last7",
    "p1_matches_last14", "p2_matches_last14",
    "p1_sets_last7", "p2_sets_last7",
    "p1_back_to_back", "p2_back_to_back",
    # Match length tendencies (last 20, same surface)
    "p1_avg_sets", "p2_avg_sets",
    "p1_tiebreak_rate", "p2_tiebreak_rate",
    # Serve stats (last 20, same surface)
    "p1_ace_per_svc_game", "p2_ace_per_svc_game",
    "p1_df_per_svc_game", "p2_df_per_svc_game",
    "p1_1st_serve_in_pct", "p2_1st_serve_in_pct",
    "p1_1st_serve_won_pct", "p2_1st_serve_won_pct",
    "p1_2nd_serve_won_pct", "p2_2nd_serve_won_pct",
    # H2H (same surface, last 3 years)
    "h2h_p1_wins", "h2h_p2_wins", "h2h_total", "h2h_p1_winrate",
    # Tournament context
    "is_best_of_5", "round_encoded",
]

# ── helpers ────────────────────────────────────────────────────────────────────

def _sets_in_score(score: str) -> int:
    """Count number of sets in a score string like '6-3 4-6 7-5'."""
    if not isinstance(score, str):
        return 0
    return len([s for s in score.strip().split() if "-" in s])


def _has_tiebreak(score: str) -> bool:
    """Return True if any set contains a tiebreak (7-6)."""
    if not isinstance(score, str):
        return False
    return "7-6" in score or "6-7" in score


def _player_matches(df: pd.DataFrame, player_id: str, before_date: pd.Timestamp) -> pd.DataFrame:
    """All matches (wins + losses) for player before given date."""
    wins = df[(df["winner_id"].astype(str) == str(player_id)) & (df["match_date"] < before_date)].copy()
    wins["_result"] = "W"
    wins["_opp_rank"] = wins["loser_rank"]
    wins["_opp_id"] = wins["loser_id"].astype(str)
    wins["_w_ace"] = wins["w_ace"]
    wins["_w_df"] = wins["w_df"]
    wins["_w_svpt"] = wins["w_svpt"]
    wins["_w_1stIn"] = wins["w_1stIn"]
    wins["_w_1stWon"] = wins["w_1stWon"]
    wins["_w_2ndWon"] = wins["w_2ndWon"]
    wins["_w_SvGms"] = wins["w_SvGms"]

    losses = df[(df["loser_id"].astype(str) == str(player_id)) & (df["match_date"] < before_date)].copy()
    losses["_result"] = "L"
    losses["_opp_rank"] = losses["winner_rank"]
    losses["_opp_id"] = losses["winner_id"].astype(str)
    losses["_w_ace"] = losses["l_ace"]
    losses["_w_df"] = losses["l_df"]
    losses["_w_svpt"] = losses["l_svpt"]
    losses["_w_1stIn"] = losses["l_1stIn"]
    losses["_w_1stWon"] = losses["l_1stWon"]
    losses["_w_2ndWon"] = losses["l_2ndWon"]
    losses["_w_SvGms"] = losses["l_SvGms"]

    combined = pd.concat([wins, losses], ignore_index=True)
    return combined.sort_values("match_date")


def _winrate(results: list[str]) -> float:
    if not results:
        return 0.5
    return sum(1 for r in results if r == "W") / len(results)


def _safe_div(a, b, default=0.0):
    try:
        return float(a) / float(b) if float(b) > 0 else default
    except (TypeError, ValueError):
        return default


# ── main feature computation ───────────────────────────────────────────────────

def compute_player_stats(
    df: pd.DataFrame,
    player_id: str,
    surface: str,
    before_date: pd.Timestamp,
) -> dict:
    """Compute all per-player features. Returns neutral defaults for unknown players."""
    pm = _player_matches(df, player_id, before_date)

    if pm.empty:
        return _neutral_player_stats()

    # ── Surface win rate (last 2 years, same surface) ──────────────────────────
    two_years_ago = before_date - pd.DateOffset(years=2)
    surf_matches = pm[(pm["surface"] == surface) & (pm["match_date"] >= two_years_ago)]
    surface_winrate = _winrate(surf_matches["_result"].tolist())
    surface_n = len(surf_matches)

    # ── Form last 5 and 10 ────────────────────────────────────────────────────
    last10 = pm.tail(10)
    last5 = pm.tail(5)

    form5_winrate = _winrate(last5["_result"].tolist())
    form10_winrate = _winrate(last10["_result"].tolist())

    # vs top-50 in last 5
    top50_last5 = last5[last5["_opp_rank"] <= 50]
    form5_vs_top50 = _winrate(top50_last5["_result"].tolist()) if len(top50_last5) > 0 else 0.5

    # sets won pct — needs score column
    def sets_won_pct(subset: pd.DataFrame) -> float:
        total_sets = sets_won = 0
        for _, row in subset.iterrows():
            n = _sets_in_score(row.get("score", ""))
            if n == 0:
                continue
            total_sets += n
            if row["_result"] == "W":
                sets_won += (n + 1) // 2  # winner always wins majority
            else:
                sets_won += n // 2
        return _safe_div(sets_won, total_sets, 0.5)

    form5_sets_pct = sets_won_pct(last5)
    form10_sets_pct = sets_won_pct(last10)

    # ── Fatigue ────────────────────────────────────────────────────────────────
    seven_days_ago = before_date - pd.Timedelta(days=7)
    fourteen_days_ago = before_date - pd.Timedelta(days=14)
    yesterday = before_date - pd.Timedelta(days=1)

    last7_matches = pm[pm["match_date"] >= seven_days_ago]
    last14_matches = pm[pm["match_date"] >= fourteen_days_ago]
    yesterday_matches = pm[pm["match_date"].dt.date == yesterday.date()]

    matches_last7 = len(last7_matches)
    matches_last14 = len(last14_matches)
    sets_last7 = int(last7_matches["score"].apply(_sets_in_score).sum())
    back_to_back = 1 if len(yesterday_matches) > 0 else 0

    # ── Match length tendencies (last 20, same surface) ────────────────────────
    surf20 = pm[pm["surface"] == surface].tail(20)
    avg_sets = surf20["score"].apply(_sets_in_score).mean() if len(surf20) > 0 else 3.0
    tiebreak_rate = surf20["score"].apply(_has_tiebreak).mean() if len(surf20) > 0 else 0.3

    # ── Serve stats (last 20, same surface) ────────────────────────────────────
    def serve_stat(col: str, subset: pd.DataFrame) -> float:
        vals = pd.to_numeric(subset[col], errors="coerce").dropna()
        return float(vals.mean()) if len(vals) > 0 else 0.0

    s = surf20
    svc_games = serve_stat("_w_SvGms", s)
    ace_per_svc = _safe_div(serve_stat("_w_ace", s), svc_games)
    df_per_svc = _safe_div(serve_stat("_w_df", s), svc_games)
    svpt = serve_stat("_w_svpt", s)
    first_in = serve_stat("_w_1stIn", s)
    first_won = serve_stat("_w_1stWon", s)
    second_pts = svpt - first_in
    second_won = serve_stat("_w_2ndWon", s)

    first_in_pct = _safe_div(first_in, svpt, 0.6)
    first_won_pct = _safe_div(first_won, first_in, 0.7)
    second_won_pct = _safe_div(second_won, second_pts, 0.5)

    return {
        "surface_winrate": surface_winrate,
        "surface_matches": surface_n,
        "form5_winrate": form5_winrate,
        "form5_vs_top50_winrate": form5_vs_top50,
        "form5_sets_won_pct": form5_sets_pct,
        "form10_winrate": form10_winrate,
        "form10_sets_won_pct": form10_sets_pct,
        "matches_last7": matches_last7,
        "matches_last14": matches_last14,
        "sets_last7": sets_last7,
        "back_to_back": back_to_back,
        "avg_sets": avg_sets if not np.isnan(avg_sets) else 3.0,
        "tiebreak_rate": tiebreak_rate if not np.isnan(tiebreak_rate) else 0.3,
        "ace_per_svc_game": ace_per_svc,
        "df_per_svc_game": df_per_svc,
        "1st_serve_in_pct": first_in_pct,
        "1st_serve_won_pct": first_won_pct,
        "2nd_serve_won_pct": second_won_pct,
    }


def _neutral_player_stats() -> dict:
    return {
        "surface_winrate": 0.5, "surface_matches": 0,
        "form5_winrate": 0.5, "form5_vs_top50_winrate": 0.5, "form5_sets_won_pct": 0.5,
        "form10_winrate": 0.5, "form10_sets_won_pct": 0.5,
        "matches_last7": 0, "matches_last14": 0, "sets_last7": 0, "back_to_back": 0,
        "avg_sets": 3.0, "tiebreak_rate": 0.3,
        "ace_per_svc_game": 0.3, "df_per_svc_game": 0.1,
        "1st_serve_in_pct": 0.6, "1st_serve_won_pct": 0.7, "2nd_serve_won_pct": 0.5,
    }


def compute_h2h(
    df: pd.DataFrame,
    p1_id: str,
    p2_id: str,
    surface: str,
    before_date: pd.Timestamp,
    years_back: int = 3,
) -> dict:
    """H2H filtered by same surface + last N years."""
    cutoff = before_date - pd.DateOffset(years=years_back)
    p1_id, p2_id = str(p1_id), str(p2_id)

    mask = (
        (df["match_date"] >= cutoff)
        & (df["match_date"] < before_date)
        & (df["surface"] == surface)
        & (
            ((df["winner_id"].astype(str) == p1_id) & (df["loser_id"].astype(str) == p2_id))
            | ((df["winner_id"].astype(str) == p2_id) & (df["loser_id"].astype(str) == p1_id))
        )
    )
    h2h_df = df[mask]

    p1_wins = int((h2h_df["winner_id"].astype(str) == p1_id).sum())
    p2_wins = int((h2h_df["winner_id"].astype(str) == p2_id).sum())
    total = p1_wins + p2_wins
    p1_winrate = _safe_div(p1_wins, total, 0.5)

    return {
        "h2h_p1_wins": p1_wins,
        "h2h_p2_wins": p2_wins,
        "h2h_total": total,
        "h2h_p1_winrate": round(p1_winrate, 3),
    }


def build_feature_vector(
    p1_stats: dict,
    p2_stats: dict,
    h2h: dict,
    p1_rank: int,
    p2_rank: int,
    p1_rank_points: int,
    p2_rank_points: int,
    is_best_of_5: bool,
    round_str: str,
) -> list[float]:
    """Assemble ordered vector matching TENNIS_FEATURE_COLS."""
    rp_total = (p1_rank_points or 0) + (p2_rank_points or 0)
    rank_points_ratio = _safe_div(p1_rank_points or 0, rp_total, 0.5)
    round_enc = ROUND_ORDER.get(str(round_str).upper(), 3)

    return [
        float(p1_rank or 300),
        float(p2_rank or 300),
        float((p2_rank or 300) - (p1_rank or 300)),
        float(p1_rank_points or 0),
        float(p2_rank_points or 0),
        float(rank_points_ratio),
        float(p1_stats["surface_winrate"]),
        float(p2_stats["surface_winrate"]),
        float(p1_stats["surface_matches"]),
        float(p2_stats["surface_matches"]),
        float(p1_stats["form5_winrate"]),
        float(p2_stats["form5_winrate"]),
        float(p1_stats["form5_vs_top50_winrate"]),
        float(p2_stats["form5_vs_top50_winrate"]),
        float(p1_stats["form5_sets_won_pct"]),
        float(p2_stats["form5_sets_won_pct"]),
        float(p1_stats["form10_winrate"]),
        float(p2_stats["form10_winrate"]),
        float(p1_stats["form10_sets_won_pct"]),
        float(p2_stats["form10_sets_won_pct"]),
        float(p1_stats["matches_last7"]),
        float(p2_stats["matches_last7"]),
        float(p1_stats["matches_last14"]),
        float(p2_stats["matches_last14"]),
        float(p1_stats["sets_last7"]),
        float(p2_stats["sets_last7"]),
        float(p1_stats["back_to_back"]),
        float(p2_stats["back_to_back"]),
        float(p1_stats["avg_sets"]),
        float(p2_stats["avg_sets"]),
        float(p1_stats["tiebreak_rate"]),
        float(p2_stats["tiebreak_rate"]),
        float(p1_stats["ace_per_svc_game"]),
        float(p2_stats["ace_per_svc_game"]),
        float(p1_stats["df_per_svc_game"]),
        float(p2_stats["df_per_svc_game"]),
        float(p1_stats["1st_serve_in_pct"]),
        float(p2_stats["1st_serve_in_pct"]),
        float(p1_stats["1st_serve_won_pct"]),
        float(p2_stats["1st_serve_won_pct"]),
        float(p1_stats["2nd_serve_won_pct"]),
        float(p2_stats["2nd_serve_won_pct"]),
        float(h2h["h2h_p1_wins"]),
        float(h2h["h2h_p2_wins"]),
        float(h2h["h2h_total"]),
        float(h2h["h2h_p1_winrate"]),
        float(1 if is_best_of_5 else 0),
        float(round_enc),
    ]
