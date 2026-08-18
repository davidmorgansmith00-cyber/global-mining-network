from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.hardware.schemas import HardwareConfig
from shared.database import open_connection


DEFAULT_STARTER_HARDWARE_ID = "starter_rusty_home_computer"
DEFAULT_STARTER_HARDWARE_NAME = "Rusty Home Computer"
DEFAULT_STARTER_HASHRATE_HPS = 12
DEFAULT_POWER_CONSUMED = 120.0
DEFAULT_POWER_CAPACITY = 120.0
DEFAULT_POWER_THROTTLE_MULTIPLIER = 1.0
DEFAULT_COOLING_EFFICIENCY = 1.0
DEFAULT_HEAT_GENERATED = 40.0
DEFAULT_COOLING_CAPACITY = 100.0
DEFAULT_COOLING_EFFICIENCY_MULTIPLIER = 1.0


@dataclass(frozen=True)
class PlayerProfileState:
    hardware_id: str
    power_consumed: float
    power_capacity: float
    power_throttle_multiplier: float
    heat_generated: float
    cooling_capacity: float
    cooling_efficiency_multiplier: float
    last_heat_dissipation_at: datetime | None
    effective_hashrate_cached: float | None
    player_tier: int
    blocks_finalized_contributed_count: int
    last_offline_progress_at: datetime | None


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
                        DEFAULT_POWER_CAPACITY,
                        DEFAULT_POWER_CAPACITY,
                        DEFAULT_COOLING_EFFICIENCY,
                    ),
                )
                cursor.execute(
                    """
                    UPDATE players
                    SET hardware_id = COALESCE(hardware_id, %s),
                        effective_hashrate_cached = COALESCE(effective_hashrate_cached, %s),
                        effective_hashrate_updated_at = COALESCE(effective_hashrate_updated_at, NOW()),
                        player_tier = COALESCE(player_tier, 1),
                        blocks_finalized_contributed_count = COALESCE(blocks_finalized_contributed_count, 0),
                        power_consumed = CASE WHEN power_consumed <= 0 THEN %s ELSE power_consumed END,
                        power_capacity = CASE WHEN power_capacity <= 0 THEN %s ELSE power_capacity END,
                        power_throttle_multiplier_cached = CASE
                            WHEN power_throttle_multiplier_cached <= 0 THEN %s
                            ELSE power_throttle_multiplier_cached
                        END,
                        heat_generated = CASE WHEN heat_generated <= 0 THEN %s ELSE heat_generated END,
                        cooling_capacity = CASE WHEN cooling_capacity <= 0 THEN %s ELSE cooling_capacity END,
                        cooling_efficiency_multiplier_cached = CASE
                            WHEN cooling_efficiency_multiplier_cached <= 0 THEN %s
                            ELSE cooling_efficiency_multiplier_cached
                        END,
                        last_heat_dissipation_at = COALESCE(last_heat_dissipation_at, NOW()),
                        last_offline_progress_at = COALESCE(last_offline_progress_at, NOW())
                    WHERE player_id = %s
                    """,
                    (
                        DEFAULT_STARTER_HARDWARE_ID,
                        float(DEFAULT_STARTER_HASHRATE_HPS),
                        DEFAULT_POWER_CONSUMED,
                        DEFAULT_POWER_CAPACITY,
                        DEFAULT_POWER_THROTTLE_MULTIPLIER,
                        DEFAULT_HEAT_GENERATED,
                        DEFAULT_COOLING_CAPACITY,
                        DEFAULT_COOLING_EFFICIENCY_MULTIPLIER,
                        player_id,
                    ),
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

    def get_profile_state(self, player_id: UUID) -> PlayerProfileState | None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        COALESCE(players.hardware_id, player_profiles.starter_hardware_id),
                        COALESCE(players.power_consumed, hardware_definitions.base_power_consumption, %s),
                        COALESCE(players.power_capacity, player_profiles.power_capacity, %s),
                        COALESCE(players.power_throttle_multiplier_cached, %s),
                        COALESCE(players.heat_generated, %s),
                        COALESCE(players.cooling_capacity, %s),
                        COALESCE(players.cooling_efficiency_multiplier_cached, %s),
                        players.last_heat_dissipation_at,
                        players.effective_hashrate_cached,
                        COALESCE(players.player_tier, 1),
                        COALESCE(players.blocks_finalized_contributed_count, 0),
                        players.last_offline_progress_at
                    FROM players
                    INNER JOIN player_profiles ON player_profiles.player_id = players.player_id
                    LEFT JOIN hardware_definitions
                        ON hardware_definitions.hardware_id = COALESCE(players.hardware_id, player_profiles.starter_hardware_id)
                    WHERE players.player_id = %s
                    """,
                    (
                        DEFAULT_POWER_CONSUMED,
                        DEFAULT_POWER_CAPACITY,
                        DEFAULT_POWER_THROTTLE_MULTIPLIER,
                        DEFAULT_HEAT_GENERATED,
                        DEFAULT_COOLING_CAPACITY,
                        DEFAULT_COOLING_EFFICIENCY_MULTIPLIER,
                        player_id,
                    ),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return PlayerProfileState(
            hardware_id=row[0],
            power_consumed=float(row[1]),
            power_capacity=float(row[2]),
            power_throttle_multiplier=float(row[3]),
            heat_generated=float(row[4]),
            cooling_capacity=float(row[5]),
            cooling_efficiency_multiplier=float(row[6]),
            last_heat_dissipation_at=row[7],
            effective_hashrate_cached=None if row[8] is None else float(row[8]),
            player_tier=int(row[9]),
            blocks_finalized_contributed_count=int(row[10]),
            last_offline_progress_at=row[11],
        )

    def get_hardware_config(self, hardware_id: str) -> HardwareConfig | None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        hardware_id,
                        base_hashrate,
                        base_power_consumption,
                        heat_generation,
                        heat_dissipation_rate_per_minute
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
            heat_dissipation_rate_per_minute=float(row[4]),
        )

    def update_effective_hashrate_cache(
        self,
        player_id: UUID,
        effective_hashrate: float,
        power_throttle_multiplier: float,
        heat_generated: float,
        cooling_efficiency_multiplier: float,
        dissipation_timestamp: datetime,
        last_offline_progress_at: datetime | None = None,
    ) -> None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE players
                    SET effective_hashrate_cached = %s,
                        power_throttle_multiplier_cached = %s,
                        heat_generated = %s,
                        cooling_efficiency_multiplier_cached = %s,
                        last_heat_dissipation_at = %s,
                        last_offline_progress_at = COALESCE(%s, last_offline_progress_at),
                        effective_hashrate_updated_at = %s
                    WHERE player_id = %s
                    """,
                    (
                        effective_hashrate,
                        power_throttle_multiplier,
                        heat_generated,
                        cooling_efficiency_multiplier,
                        dissipation_timestamp,
                        last_offline_progress_at,
                        dissipation_timestamp,
                        player_id,
                    ),
                )
            connection.commit()

    def get_blocks_finalized_contributed_count(self, player_id: UUID) -> int:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT block_number)
                    FROM economy_player_ledger_entries
                    WHERE player_id = %s
                      AND entry_type = 'block.finalized.player_reward.v1'
                    """,
                    (str(player_id),),
                )
                row = cursor.fetchone()
        return 0 if row is None or row[0] is None else int(row[0])

    def update_player_progression(
        self,
        player_id: UUID,
        *,
        blocks_finalized_contributed_count: int,
        player_tier: int,
    ) -> None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE players
                    SET blocks_finalized_contributed_count = %s,
                        player_tier = %s,
                        updated_at = NOW()
                    WHERE player_id = %s
                    """,
                    (blocks_finalized_contributed_count, player_tier, player_id),
                )
            connection.commit()

    def update_profile_hardware_state(
        self,
        player_id: UUID,
        *,
        hardware_id: str | None = None,
        power_consumed: float | None = None,
        power_capacity: float | None = None,
        cooling_capacity: float | None = None,
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
                    UPDATE players
                    SET power_consumed = COALESCE(%s, power_consumed),
                        power_capacity = COALESCE(%s, power_capacity),
                        cooling_capacity = COALESCE(%s, cooling_capacity),
                        updated_at = NOW()
                    WHERE player_id = %s
                    """,
                    (power_consumed, power_capacity, cooling_capacity, player_id),
                )
                cursor.execute(
                    """
                    UPDATE player_profiles
                    SET power_capacity = COALESCE(%s, power_capacity),
                        updated_at = NOW()
                    WHERE player_id = %s
                    """,
                    (power_capacity, player_id),
                )
            connection.commit()
