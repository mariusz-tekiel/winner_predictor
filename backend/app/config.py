from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    football_api_key: str = ""
    apifootball_api_key: str = ""
    model_dir: str = "data/models"
    cache_db: str = "data/cache.db"
    debug: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

Path(settings.model_dir).mkdir(parents=True, exist_ok=True)
Path(settings.cache_db).parent.mkdir(parents=True, exist_ok=True)
