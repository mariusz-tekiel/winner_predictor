"""
Tennis model training pipeline.
CPU-heavy work runs in a thread pool executor so the async event loop
stays free and the HTTP response is returned immediately.
"""
import asyncio
import numpy as np
from datetime import datetime
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss

import tennis.csv_loader as loader
import tennis.model_store as store
from tennis.feature_engineering import (
    compute_player_stats,
    compute_h2h,
    build_feature_vector,
    TENNIS_FEATURE_COLS,
)

_progress: dict[str, dict] = {}


def get_progress(task_id: str) -> dict:
    return _progress.get(task_id, {"status": "not_found"})


async def train_async(tour: str, years: list[int], task_id: str):
    """Schedules training in a thread pool — returns immediately to the event loop."""
    _progress[task_id] = {"status": "fetching", "step": 0, "total": 0}
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _train_sync, tour, years, task_id)


def _train_sync(tour: str, years: list[int], task_id: str):
    """Blocking training function — runs in a thread pool."""
    try:
        df = loader.load_matches_df(tour, years, use_cache=False)

        if df.empty:
            _progress[task_id] = {
                "status": "error",
                "message": "Brak plików CSV. Pobierz dane skryptem download_tennis_csv.py",
            }
            return

        finished = df.dropna(subset=["score"]).copy()
        finished = finished.sort_values("match_date").reset_index(drop=True)

        _progress[task_id]["status"] = "building_features"
        _progress[task_id]["total"] = len(finished) * 2  # *2 for symmetry augmentation

        X, y = [], []
        step = 0

        for _, row in finished.iterrows():
            match_date = row["match_date"]
            surface = row["surface"]
            winner_id = str(row["winner_id"])
            loser_id = str(row["loser_id"])
            w_rank = int(row.get("winner_rank") or 300)
            l_rank = int(row.get("loser_rank") or 300)
            w_pts = int(row.get("winner_rank_points") or 0)
            l_pts = int(row.get("loser_rank_points") or 0)
            best_of = int(row.get("best_of") or 3)
            round_str = str(row.get("round") or "R32")

            w_stats = compute_player_stats(df, winner_id, surface, match_date)
            l_stats = compute_player_stats(df, loser_id, surface, match_date)
            h2h_wl = compute_h2h(df, winner_id, loser_id, surface, match_date)
            h2h_lw = compute_h2h(df, loser_id, winner_id, surface, match_date)

            is_bo5 = best_of == 5

            # Symmetry: winner as p1 (label=1)
            fv1 = build_feature_vector(
                w_stats, l_stats, h2h_wl,
                w_rank, l_rank, w_pts, l_pts, is_bo5, round_str
            )
            X.append(fv1)
            y.append(1)
            step += 1
            _progress[task_id]["step"] = step

            # Symmetry: loser as p1 (label=0)
            fv2 = build_feature_vector(
                l_stats, w_stats, h2h_lw,
                l_rank, w_rank, l_pts, w_pts, is_bo5, round_str
            )
            X.append(fv2)
            y.append(0)
            step += 1
            _progress[task_id]["step"] = step

        if len(X) < 40:
            _progress[task_id] = {
                "status": "error",
                "message": f"Za mało danych: {len(X) // 2} meczów. Potrzeba min. 20.",
            }
            return

        X = np.array(X, dtype=float)
        y = np.array(y)

        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        _progress[task_id]["status"] = "training"

        base = HistGradientBoostingClassifier(
            max_iter=300,
            max_depth=6,
            learning_rate=0.05,
            min_samples_leaf=20,
            random_state=42,
        )
        model = CalibratedClassifierCV(base, method="isotonic", cv=3)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]

        accuracy = float(accuracy_score(y_test, y_pred))
        ll = float(log_loss(y_test, y_prob))
        brier = float(brier_score_loss(y_test, y_prob))

        metadata = {
            "tour": tour,
            "years": years,
            "trained_at": datetime.utcnow().isoformat(),
            "sample_count": len(finished),
            "accuracy": round(accuracy, 4),
            "log_loss": round(ll, 4),
            "brier_score": round(brier, 4),
            "feature_cols": TENNIS_FEATURE_COLS,
        }

        store.save(model, metadata)
        loader.invalidate_cache()

        _progress[task_id] = {
            "status": "done",
            "accuracy": round(accuracy * 100, 1),
            "sample_count": len(finished),
            "brier_score": round(brier, 4),
        }

    except Exception as e:
        _progress[task_id] = {"status": "error", "message": str(e)}
