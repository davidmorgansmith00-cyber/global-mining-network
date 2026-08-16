from __future__ import annotations

from uuid import UUID

from shared.database import open_connection


class PlayerRepository:
    def create_profile(self, player_id: UUID) -> None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO player_profiles (player_id, starter_hardware_id, starter_hardware_name, starter_hashrate_hps)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (player_id) DO NOTHING
                    """,
                    (player_id, "starter_rusty_home_computer", "Rusty Home Computer", 12),
                )
            connection.commit()

    def get_profile(self, player_id: UUID) -> tuple[str, str, int] | None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT starter_hardware_id, starter_hardware_name, starter_hashrate_hps
                    FROM player_profiles
                    WHERE player_id = %s
                    """,
                    (player_id,),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return row[0], row[1], row[2]