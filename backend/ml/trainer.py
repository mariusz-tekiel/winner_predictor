"""
Orchestrates data collection + model training.
Designed to run in a thread pool (not async) so it can block freely.
"""
import asyncio
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.metrics import accuracy_score, classification_report

import services.source_router as api
from ml.feature_engineering import (
    compute_form,
    compute_standings_map,
    compute_h2h,
    build_feature_vector,
    get_match_outcome,
    FEATURE_COLS,
)
import ml.model_store as store

# Progress shared dict — keyed by task_id
_progress: dict[str, dict] = {}


def get_progress(task_id: str) -> dict:
    return _progress.get(task_id, {"status": "not_found"})


async def train_async(competition_code: str, seasons: list[int], task_id: str):
    """Main training coroutine — runs inside background task."""
    _progress[task_id] = {"status": "fetching", "step": 0, "total": 0, "accuracy": None}

    try:
        # Fetch all matches — current season always, historical only if provided
        all_matches = []

        for season in seasons:
            try:
                data = await api.get_all_matches(competition_code, season)
                all_matches.extend(data.get("matches", []))
            except Exception:
                # Free tier blocks historical seasons (403) — skip silently
                pass

        # Current season (always available on free tier)
        current_data = await api.get_all_matches(competition_code)
        all_matches.extend(current_data.get("matches", []))

        # Deduplicate by match id
        seen = set()
        unique_matches = []
        for m in all_matches:
            if m["id"] not in seen:
                seen.add(m["id"])
                unique_matches.append(m)
        all_matches = unique_matches

        finished = [m for m in all_matches if m.get("status") == "FINISHED"]
        finished.sort(key=lambda m: m["utcDate"])

        standings_data = await api.get_standings(competition_code)
        standings_map = compute_standings_map(standings_data)

        _progress[task_id]["status"] = "building_features"
        _progress[task_id]["total"] = len(finished)

        X, y = [], []
        for i, match in enumerate(finished):
            _progress[task_id]["step"] = i + 1

            outcome = get_match_outcome(match)
            if outcome is None:
                continue

            home_id = match["homeTeam"]["id"]
            away_id = match["awayTeam"]["id"]
            match_date = match["utcDate"]
            matchday = match.get("matchday", 1) or 1

            home_form = compute_form(all_matches, home_id, match_date)
            away_form = compute_form(all_matches, away_id, match_date)

            # H2H from in-memory matches (no extra API call)
            h2h_matches = [
                m for m in all_matches
                if (
                    m.get("status") == "FINISHED"
                    and m["utcDate"] < match_date
                    and {m["homeTeam"]["id"], m["awayTeam"]["id"]} == {home_id, away_id}
                )
            ]
            h2h_data = {"matches": h2h_matches}
            h2h = compute_h2h(h2h_data, home_id)

            fv = build_feature_vector(
                home_form, away_form, standings_map, h2h,
                home_id, away_id, matchday
            )
            X.append(fv)
            y.append(outcome)

        if len(X) < 20:
            _progress[task_id] = {
                "status": "error",
                "message": f"Za mało danych: {len(X)} meczów. Potrzeba min. 20."
            }
            return

        X = np.array(X, dtype=float)
        y = np.array(y)

        # Time-based split (no shuffle!)
        split = int(len(X) * 0.8)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        _progress[task_id]["status"] = "training"

        model = RandomForestClassifier(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=10,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        accuracy = float(accuracy_score(y_test, y_pred))

        metadata = {
            "competition": competition_code,
            "trained_at": datetime.utcnow().isoformat(),
            "sample_count": len(X),
            "accuracy": round(accuracy, 4),
            "feature_cols": FEATURE_COLS,
            "classes": list(model.classes_),
        }

        store.save(model, metadata)

        _progress[task_id] = {
            "status": "done",
            "accuracy": round(accuracy * 100, 1),
            "sample_count": len(X),
        }

    except Exception as e:
        _progress[task_id] = {"status": "error", "message": str(e)}
