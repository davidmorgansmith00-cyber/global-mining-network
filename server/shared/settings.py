import os

from pydantic import BaseModel


def _read_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


class Settings(BaseModel):
    environment: str = os.getenv("ENVIRONMENT", "local")
    api_v1_prefix: str = "/api/v1"
    database_url: str = os.getenv("DATABASE_URL", "")
    redis_url: str = os.getenv("REDIS_URL", "")
    maintenance_auth_header: str = os.getenv("MAINTENANCE_AUTH_HEADER", "X-Maintenance-Token")
    maintenance_auth_token: str = os.getenv("MAINTENANCE_AUTH_TOKEN", "local-maintenance-token")
    maintenance_auth_previous_token: str = os.getenv("MAINTENANCE_AUTH_PREVIOUS_TOKEN", "")
    maintenance_auth_current_token_scope_label: str = os.getenv(
        "MAINTENANCE_AUTH_CURRENT_TOKEN_SCOPE_LABEL", "current"
    )
    maintenance_auth_previous_token_scope_label: str = os.getenv(
        "MAINTENANCE_AUTH_PREVIOUS_TOKEN_SCOPE_LABEL", "previous"
    )
    maintenance_auth_unknown_token_scope_label: str = os.getenv(
        "MAINTENANCE_AUTH_UNKNOWN_TOKEN_SCOPE_LABEL", "unknown"
    )
    maintenance_cleanup_rate_limit_window_seconds: int = int(
        os.getenv("MAINTENANCE_CLEANUP_RATE_LIMIT_WINDOW_SECONDS", "60")
    )
    maintenance_cleanup_rate_limit_max_requests: int = int(
        os.getenv("MAINTENANCE_CLEANUP_RATE_LIMIT_MAX_REQUESTS", "6")
    )
    maintenance_cleanup_rate_limit_persistence_enabled: bool = _read_bool(
        os.getenv("MAINTENANCE_CLEANUP_RATE_LIMIT_PERSISTENCE_ENABLED"),
        default=True,
    )


settings = Settings()