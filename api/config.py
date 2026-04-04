from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

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

    environment: str = "development"

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

    # Journey orchestrator rollout controls
    journey_orchestrator_v2_enabled: bool = False
    journey_orchestrator_v2_allowlist_user_ids: str = ""
    journey_orchestrator_v2_rollout_percent: int = 0

    # Concurrency/idempotency protection for continue/advance APIs
    journey_orchestrator_lock_ttl_seconds: int = 15
    journey_orchestrator_idempotency_ttl_seconds: int = 300

    def is_production(self) -> bool:
        env = str(self.environment or "").strip().lower()
        return env in {"prod", "production"}

    def validate_runtime(self) -> None:
        """Fail fast on insecure production defaults."""
        if not self.is_production():
            return

        issues: list[str] = []
        if str(self.secret_key or "").strip() == "change-me-in-production":
            issues.append("COGNIMAP_SECRET_KEY must be set to a secure value")

        if any(str(origin).strip() == "*" for origin in self.cors_origins):
            issues.append("COGNIMAP_CORS_ORIGINS cannot contain '*' in production")

        if _is_local_url(self.database_url):
            issues.append("COGNIMAP_DATABASE_URL must not point to localhost in production")
        if _is_local_url(self.database_url_sync):
            issues.append("COGNIMAP_DATABASE_URL_SYNC must not point to localhost in production")
        if _is_local_url(self.redis_url):
            issues.append("COGNIMAP_REDIS_URL must not point to localhost in production")

        if issues:
            raise RuntimeError("Invalid production configuration: " + "; ".join(issues))


def _is_local_url(raw: str) -> bool:
    value = str(raw or "").strip()
    if not value:
        return False
    try:
        host = (urlparse(value).hostname or "").lower()
    except Exception:
        host = ""
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    lowered = value.lower()
    return any(token in lowered for token in ("@localhost", "@127.0.0.1", "@[::1]"))


@lru_cache(maxsize=1)
def get_api_settings() -> APISettings:
    return APISettings()
