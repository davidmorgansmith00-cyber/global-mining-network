from __future__ import annotations

from contextlib import contextmanager
import os
from typing import Any, Iterator

from shared.settings import settings


def database_is_configured() -> bool:
    return bool(os.getenv("DATABASE_URL") or settings.database_url)


@contextmanager
def open_connection() -> Iterator[Any]:
    database_url = os.getenv("DATABASE_URL") or settings.database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    import psycopg

    with psycopg.connect(database_url) as connection:
        yield connection