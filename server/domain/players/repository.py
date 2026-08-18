from __future__ import annotations

from uuid import UUID

from domain.hardware.schemas import HardwareConfig
from shared.database import open_connection


DEFAULT_STARTER_HARDWARE_ID = "starter_rusty_home_computer"
DEFAULT_STARTER_HARDWARE_NAME = "Rusty Home Computer"
DEFAULT_STARTER_HASHRATE_HPS = 12
DEFAULT_POWER_AVAILABLE = 120.0
DEFAULT_POWER_CAPACITY = 120.0
DEFAULT_COOLING_EFFICIENCY = 1.0


class PlayerRepository:
    def create_profile(self, player_id: UUID) -> None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO player_profiles (
                        player_id,
                        starter_hardware_id,
                        starter_hardware_name,
                        starter_hashrate_hps,
                        power_available,
                        power_capacity,
                        cooling_efficiency
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (player_id) DO NOTHING
                    """,
                    (
                        player_id,
                        DEFAULT_STARTER_HARDWARE_ID,
                        DEFAULT_STARTER_HARDWARE_NAME,
                        DEFAULT_STARTER_HASHRATE_HPS,
                        DEFAULT_POWER_AVAILABLE,
                        DEFAULT_POWER_CAPACITY,
                        DEFAULT_COOLING_EFFICIENCY,
                    ),
                )
                cursor.execute(
                    """
                    UPDATE players
                    SET hardware_id = COALESCE(hardware_id, %s),
                        effective_hashrate_cached = COALESCE(effective_hashrate_cached, %s),
                        effective_hashrate_updated_at = COALESCE(effective_hashrate_updated_at, NOW())
                    WHERE player_id = %s
                    """,
                    (DEFAULT_STARTER_HARDWARE_ID, float(DEFAULT_STARTER_HASHRATE_HPS), player_id),
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

    def get_profile_state(self, player_id: UUID) -> tuple[str, float, float, float, float | None] | None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        COALESCE(players.hardware_id, player_profiles.starter_hardware_id),
                        player_profiles.power_available,
                        player_profiles.power_capacity,
                        player_profiles.cooling_efficiency,
                        players.effective_hashrate_cached
                    FROM players
                    INNER JOIN player_profiles ON player_profiles.player_id = players.player_id
                    WHERE players.player_id = %s
                    """,
                    (player_id,),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return row[0], float(row[1]), float(row[2]), float(row[3]), None if row[4] is None else float(row[4])

    def get_hardware_config(self, hardware_id: str) -> HardwareConfig | None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT hardware_id, base_hashrate, base_power_consumption, heat_generation
                    FROM hardware_definitions
                    WHERE hardware_id = %s
                    """,
                    (hardware_id,),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return HardwareConfig(
            hardware_id=row[0],
            base_hashrate=float(row[1]),
            base_power_consumption=float(row[2]),
            heat_generation=float(row[3]),
        )

    def update_effective_hashrate_cache(self, player_id: UUID, effective_hashrate: float) -> None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE players
                    SET effective_hashrate_cached = %s,
                        effective_hashrate_updated_at = NOW()
                    WHERE player_id = %s
                    """,
                    (effective_hashrate, player_id),
                )
            connection.commit()

    def update_profile_hardware_state(
        self,
        player_id: UUID,
        *,
        hardware_id: str | None = None,
        power_available: float | None = None,
        power_capacity: float | None = None,
        cooling_efficiency: float | None = None,
    ) -> None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                if hardware_id is not None:
                    cursor.execute(
                        """
                        UPDATE players
                        SET hardware_id = %s
                        WHERE player_id = %s
                        """,
                        (hardware_id, player_id),
                    )
                cursor.execute(
                    """
                    UPDATE player_profiles
                    SET power_available = COALESCE(%s, power_available),
                        power_capacity = COALESCE(%s, power_capacity),
                        cooling_efficiency = COALESCE(%s, cooling_efficiency),
                        updated_at = NOW()
                    WHERE player_id = %s
                    """,
                    (power_available, power_capacity, cooling_efficiency, player_id),
                )
            connection.commit()