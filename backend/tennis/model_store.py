import json
import joblib
from pathlib import Path
from app.config import settings

MODEL_DIR = Path(settings.model_dir)

_MODEL_FILE = MODEL_DIR / "tennis_model.joblib"
_META_FILE = MODEL_DIR / "tennis_metadata.json"

_cached_model = None


def save(model, metadata: dict):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, _MODEL_FILE)
    with open(_META_FILE, "w") as f:
        json.dump(metadata, f, indent=2)
    global _cached_model
    _cached_model = model


def load():
    global _cached_model
    if _cached_model is not None:
        return _cached_model
    if not _MODEL_FILE.exists():
        return None
    _cached_model = joblib.load(_MODEL_FILE)
    return _cached_model


def get_metadata() -> dict | None:
    if not _META_FILE.exists():
        return None
    with open(_META_FILE) as f:
        return json.load(f)


def is_trained() -> bool:
    return _MODEL_FILE.exists()
