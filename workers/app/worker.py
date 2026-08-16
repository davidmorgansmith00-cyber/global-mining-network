from datetime import datetime, UTC
import json
import random
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import logging

from app.database import database_is_configured
from app.settings import settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("gmn.worker")


def _compute_startup_jitter_seconds(
    *,
    max_jitter_seconds: int,
    random_fraction: float | None = None,
) -> int:
    if max_jitter_seconds <= 0:
        return 0

    fraction = random.random() if random_fraction is None else random_fraction
    bounded_fraction = min(1.0, max(0.0, fraction))
    return int(round(bounded_fraction * max_jitter_seconds))


def _compute_sleep_seconds(
    *,
    elapsed_seconds: float,
    base_interval_seconds: int,
    consecutive_failures: int,
    backoff_max_seconds: int,
) -> int:
    if consecutive_failures <= 0:
        return max(1, base_interval_seconds - int(elapsed_seconds))

    backoff = min(backoff_max_seconds, base_interval_seconds * (2 ** (consecutive_failures - 1)))
    return max(1, backoff - int(elapsed_seconds))


def _build_cleanup_url() -> str:
    query = urlencode(
        {
            "event_retention_seconds": settings.blockchain_event_retention_seconds,
            "checkpoint_retention_seconds": settings.blockchain_checkpoint_retention_seconds,
            "max_network_events": settings.blockchain_max_network_events,
        }
    )
    return f"{settings.api_base_url}{settings.api_v1_prefix}/blockchain/maintenance/cleanup?{query}"


def _resolve_maintenance_auth_token(*, token_file_path: str, fallback_token: str) -> str:
    if token_file_path:
        try:
            with open(token_file_path, "r", encoding="utf-8") as handle:
                file_token = handle.read().strip()
            if file_token:
                return file_token
            logger.warning("maintenance_token_file_empty path=%s using_fallback=true", token_file_path)
        except OSError as exc:
            logger.warning(
                "maintenance_token_file_unreadable path=%s error_type=%s error=%s using_fallback=true",
                token_file_path,
                type(exc).__name__,
                str(exc),
            )
    return fallback_token


def _maintenance_token_source_mode(*, token_file_path: str) -> str:
    return "file" if bool(token_file_path) else "env"


def _should_warn_missing_maintenance_token(
    *,
    environment: str,
    token_file_path: str,
    fallback_token: str,
) -> bool:
    if environment.strip().lower() == "local":
        return False
    return not token_file_path and not fallback_token


def _run_cleanup_once() -> dict[str, int]:
    url = _build_cleanup_url()
    maintenance_token = _resolve_maintenance_auth_token(
        token_file_path=settings.maintenance_auth_token_file,
        fallback_token=settings.maintenance_auth_token,
    )
    request = Request(
        url=url,
        method="POST",
        headers={settings.maintenance_auth_header: maintenance_token},
    )
    with urlopen(request, timeout=settings.blockchain_cleanup_timeout_seconds) as response:  # nosec B310
        body = response.read().decode("utf-8")
    payload = json.loads(body)
    return {
        "deleted_network_events_by_age": int(payload.get("deleted_network_events_by_age", 0)),
        "deleted_network_events_by_count": int(payload.get("deleted_network_events_by_count", 0)),
        "deleted_client_checkpoints": int(payload.get("deleted_client_checkpoints", 0)),
    }


def main() -> None:
    timestamp = datetime.now(UTC).isoformat()
    logger.info(
        "worker_started %s environment=%s database_configured=%s cleanup_enabled=%s interval_seconds=%s",
        timestamp,
        settings.environment,
        str(database_is_configured()).lower(),
        str(settings.blockchain_cleanup_enabled).lower(),
        settings.blockchain_cleanup_interval_seconds,
    )

    if not settings.blockchain_cleanup_enabled:
        logger.info("cleanup_scheduler_disabled")
        return

    startup_jitter_seconds = _compute_startup_jitter_seconds(
        max_jitter_seconds=settings.blockchain_cleanup_startup_jitter_seconds,
    )
    if startup_jitter_seconds > 0:
        logger.info("cleanup_scheduler_startup_jitter_sleep seconds=%s", startup_jitter_seconds)
        time.sleep(startup_jitter_seconds)

    logger.info(
        "cleanup_scheduler_auth_token_source mode=%s",
        _maintenance_token_source_mode(token_file_path=settings.maintenance_auth_token_file),
    )
    if _should_warn_missing_maintenance_token(
        environment=settings.environment,
        token_file_path=settings.maintenance_auth_token_file,
        fallback_token=settings.maintenance_auth_token,
    ):
        logger.warning(
            "cleanup_scheduler_missing_maintenance_token environment=%s token_file_configured=false env_token_configured=false",
            settings.environment,
        )

    runs_total = 0
    failures_total = 0
    consecutive_failures = 0
    deleted_events_total = 0
    deleted_checkpoints_total = 0

    while True:
        started = time.monotonic()
        try:
            result = _run_cleanup_once()
            runs_total += 1
            consecutive_failures = 0
            deleted_events = result["deleted_network_events_by_age"] + result["deleted_network_events_by_count"]
            deleted_events_total += deleted_events
            deleted_checkpoints_total += result["deleted_client_checkpoints"]
            logger.info(
                "cleanup_job_completed deleted_network_events_by_age=%s deleted_network_events_by_count=%s "
                "deleted_client_checkpoints=%s runs_total=%s failures_total=%s "
                "deleted_network_events_total=%s deleted_client_checkpoints_total=%s",
                result["deleted_network_events_by_age"],
                result["deleted_network_events_by_count"],
                result["deleted_client_checkpoints"],
                runs_total,
                failures_total,
                deleted_events_total,
                deleted_checkpoints_total,
            )
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            failures_total += 1
            consecutive_failures += 1
            backoff_seconds = min(
                settings.blockchain_cleanup_backoff_max_seconds,
                settings.blockchain_cleanup_interval_seconds * (2 ** (consecutive_failures - 1)),
            )
            logger.warning(
                "cleanup_job_failed failures_total=%s consecutive_failures=%s backoff_seconds=%s "
                "error_type=%s error=%s",
                failures_total,
                consecutive_failures,
                backoff_seconds,
                type(exc).__name__,
                str(exc),
            )

        elapsed = time.monotonic() - started
        sleep_seconds = _compute_sleep_seconds(
            elapsed_seconds=elapsed,
            base_interval_seconds=settings.blockchain_cleanup_interval_seconds,
            consecutive_failures=consecutive_failures,
            backoff_max_seconds=settings.blockchain_cleanup_backoff_max_seconds,
        )
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()