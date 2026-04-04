from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class APISettings(BaseSettings):

    model_config = {
        "env_prefix": "COGNIMAP_",
        "env_file": str(BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    database_url: str = "postgresql+asyncpg://cognimap_admin:secretpassword@localhost:5432/cognimap"
    database_url_sync: str = "postgresql://cognimap_admin:secretpassword@localhost:5432/cognimap"

    redis_url: str = "redis://localhost:6379/0"

    # Override this in environment variables for production deployments.
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    cors_origins: list[str] = ["*"]

    huggingface_api_token: str = ""
    use_hf_moderation: bool = True
    hf_moderation_model: str = "unitary/toxic-bert"
    hf_moderation_timeout_seconds: float = 0.8
    hf_moderation_toxicity_threshold: float = 0.72
    use_hf_name_detection: bool = True
    hf_name_detection_model: str = "dslim/bert-base-NER"
    hf_name_detection_timeout_seconds: float = 0.8
    hf_person_entity_threshold: float = 0.9


@lru_cache(maxsize=1)
def get_api_settings() -> APISettings:
    return APISettings()
