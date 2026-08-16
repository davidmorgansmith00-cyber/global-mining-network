from __future__ import annotations

import os
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "database" / "migrations"


def iter_migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def apply_migrations() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is required")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for migration_file in iter_migration_files():
                cursor.execute(migration_file.read_text(encoding="utf-8"))
        connection.commit()


if __name__ == "__main__":
    apply_migrations()