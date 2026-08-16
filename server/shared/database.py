from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from shared.settings import settings


def database_is_configured() -> bool:
    return bool(settings.database_url)


@contextmanager
def open_connection() -> Iterator[Any]:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    import psycopg

    with psycopg.connect(settings.database_url) as connection:
        yield connection