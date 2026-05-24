"""
Loads Jeff Sackmann CSV files from disk into a normalized DataFrame.
Files expected in settings.tennis_csv_dir:
  atp_{YEAR}.csv
  wta_{YEAR}.csv
  atp_challenger_{YEAR}.csv
"""
import pandas as pd
from pathlib import Path
from app.config import settings
from tennis.constants import SURFACE_NORM

_CSV_DIR = Path(settings.tennis_csv_dir)

# Module-level cache: key -> DataFrame
_cache: dict[str, pd.DataFrame] = {}

_REQUIRED_COLS = [
    "tourney_id", "tourney_name", "surface", "tourney_date",
    "winner_id", "winner_name", "winner_rank", "winner_rank_points",
    "loser_id", "loser_name", "loser_rank", "loser_rank_points",
    "score", "best_of", "round", "minutes",
]

_SERVE_COLS = [
    "w_ace", "w_df", "w_svpt", "w_1stIn", "w_1stWon", "w_2ndWon", "w_SvGms",
    "l_ace", "l_df", "l_svpt", "l_1stIn", "l_1stWon", "l_2ndWon", "l_SvGms",
]


def _csv_path(tour: str, year: int) -> Path:
    if tour == "challenger":
        return _CSV_DIR / f"atp_challenger_{year}.csv"
    return _CSV_DIR / f"{tour}_{year}.csv"


def _load_single(tour: str, year: int) -> pd.DataFrame | None:
    path = _csv_path(tour, year)
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception:
        return None

    # Keep only columns we need (optional serve cols may be absent)
    cols_present = [c for c in _REQUIRED_COLS if c in df.columns]
    serve_present = [c for c in _SERVE_COLS if c in df.columns]
    df = df[cols_present + serve_present].copy()

    # Add missing serve cols as NaN
    for c in _SERVE_COLS:
        if c not in df.columns:
            df[c] = float("nan")

    # Parse date
    df["match_date"] = pd.to_datetime(df["tourney_date"].astype(str), format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["match_date"])

    # Normalize surface
    df["surface"] = df["surface"].map(SURFACE_NORM).fillna("hard")

    # Remove walkovers and retirements
    df = df[df["score"].notna()]
    df = df[~df["score"].str.contains(r"W/O|RET|DEF|nbsp", na=True, case=False)]

    # Normalize numeric columns
    for col in ["winner_rank", "winner_rank_points", "loser_rank", "loser_rank_points", "minutes", "best_of"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Fill missing ranks with 300 (unranked)
    df["winner_rank"] = df["winner_rank"].fillna(300)
    df["loser_rank"] = df["loser_rank"].fillna(300)
    df["winner_rank_points"] = df["winner_rank_points"].fillna(0)
    df["loser_rank_points"] = df["loser_rank_points"].fillna(0)

    # Encode round
    df["tour"] = tour
    df["match_id"] = (
        df["tourney_id"].astype(str) + "_"
        + df["winner_id"].astype(str) + "_"
        + df["loser_id"].astype(str)
    )

    return df.reset_index(drop=True)


def load_matches_df(tour: str, years: list[int], use_cache: bool = True) -> pd.DataFrame:
    """Load and concatenate all CSV files for given tour and years."""
    cache_key = f"{tour}_{min(years)}_{max(years)}"
    if use_cache and cache_key in _cache:
        return _cache[cache_key]

    frames = []
    for year in years:
        df = _load_single(tour, year)
        if df is not None:
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    result = result.sort_values("match_date").reset_index(drop=True)

    if use_cache:
        _cache[cache_key] = result
    return result


def invalidate_cache():
    """Clear in-memory cache after training."""
    _cache.clear()


def csv_status() -> dict:
    """Return which CSV files are present on disk."""
    status = {}
    for tour in ["atp", "wta", "challenger"]:
        status[tour] = []
        for year in range(2010, 2026):
            path = _csv_path(tour, year)
            if path.exists():
                status[tour].append(year)
    return status
