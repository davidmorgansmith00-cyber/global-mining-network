import os


def _read_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _read_int(value: str | None, *, default: int, minimum: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(parsed, minimum)


class WorkerSettings:
    environment: str = os.getenv("ENVIRONMENT", "local")
    database_url: str = os.getenv("DATABASE_URL", "")
    redis_url: str = os.getenv("REDIS_URL", "")
    api_base_url: str = os.getenv("API_BASE_URL", "http://api:8000").rstrip("/")
    api_v1_prefix: str = os.getenv("API_V1_PREFIX", "/api/v1")
    maintenance_auth_header: str = os.getenv("MAINTENANCE_AUTH_HEADER", "X-Maintenance-Token")
    maintenance_auth_token: str = os.getenv("MAINTENANCE_AUTH_TOKEN", "local-maintenance-token")
    maintenance_auth_token_file: str = os.getenv("MAINTENANCE_AUTH_TOKEN_FILE", "")

    blockchain_cleanup_enabled: bool = _read_bool(
        os.getenv("BLOCKCHAIN_CLEANUP_ENABLED"),
        default=True,
    )
    blockchain_cleanup_interval_seconds: int = _read_int(
        os.getenv("BLOCKCHAIN_CLEANUP_INTERVAL_SECONDS"),
        default=300,
        minimum=30,
    )
    blockchain_cleanup_startup_jitter_seconds: int = _read_int(
        os.getenv("BLOCKCHAIN_CLEANUP_STARTUP_JITTER_SECONDS"),
        default=0,
        minimum=0,
    )
    blockchain_cleanup_backoff_max_seconds: int = _read_int(
        os.getenv("BLOCKCHAIN_CLEANUP_BACKOFF_MAX_SECONDS"),
        default=1800,
        minimum=30,
    )
    blockchain_cleanup_timeout_seconds: int = _read_int(
        os.getenv("BLOCKCHAIN_CLEANUP_TIMEOUT_SECONDS"),
        default=10,
        minimum=1,
    )
    blockchain_event_retention_seconds: int = _read_int(
        os.getenv("BLOCKCHAIN_EVENT_RETENTION_SECONDS"),
        default=60 * 60 * 24,
        minimum=60,
    )
    blockchain_checkpoint_retention_seconds: int = _read_int(
        os.getenv("BLOCKCHAIN_CHECKPOINT_RETENTION_SECONDS"),
        default=60 * 60 * 24 * 7,
        minimum=60,
    )
    blockchain_max_network_events: int = _read_int(
        os.getenv("BLOCKCHAIN_MAX_NETWORK_EVENTS"),
        default=100_000,
        minimum=1,
    )


settings = WorkerSettings()