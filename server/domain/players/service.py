from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from domain.hardware.schemas import CoolingState, HardwareConfig, PowerState
from domain.hardware.service import GmnHardwareHashrateService
from domain.players.repository import (
    DEFAULT_COOLING_CAPACITY,
    DEFAULT_COOLING_EFFICIENCY_MULTIPLIER,
    DEFAULT_HEAT_GENERATED,
    DEFAULT_POWER_CAPACITY,
    DEFAULT_POWER_CONSUMED,
    DEFAULT_POWER_THROTTLE_MULTIPLIER,
    PlayerRepository,
)
from domain.players.schemas import BootstrapResponse, PlayerProfileResponse, StarterMachine
from shared.database import database_is_configured


DEFAULT_PLAYER_ID = "player_placeholder"
DEFAULT_HARDWARE_ID = "starter_rusty_home_computer"
DEFAULT_HARDWARE_NAME = "Rusty Home Computer"
DEFAULT_HASHRATE_HPS = 12.0


class PlayerBootstrapService:
    def __init__(self) -> None:
        self.repository = PlayerRepository()

    def bootstrap(self, player_id: str | None = None) -> BootstrapResponse:
        if database_is_configured() and player_id is not None:
            profile = self.repository.get_profile(UUID(player_id))
            if profile is not None:
                hardware_id, name, hashrate_hps = profile
                return BootstrapResponse(
                    player_id=player_id,
                    starter_machine=StarterMachine(
                        hardware_id=hardware_id,
                        name=name,
                        hashrate_hps=hashrate_hps,
                    ),
                )

        return BootstrapResponse(
            player_id=player_id or DEFAULT_PLAYER_ID,
            starter_machine=StarterMachine(
                hardware_id=DEFAULT_HARDWARE_ID,
                name=DEFAULT_HARDWARE_NAME,
                hashrate_hps=int(DEFAULT_HASHRATE_HPS),
            ),
        )


class PlayerProfileService:
    def __init__(self) -> None:
        self.repository = PlayerRepository()
        self.hashrate_service = GmnHardwareHashrateService()

    def get_profile(self, player_id: str | None = None) -> PlayerProfileResponse:
        if database_is_configured() and player_id is not None:
            profile = self.repository.get_profile_state(UUID(player_id))
            if profile is not None:
                (
                    hardware_id,
                    power_consumed,
                    power_capacity,
                    _cached_power_throttle,
                    heat_generated_stored,
                    cooling_capacity,
                    _cached_cooling_multiplier,
                    last_heat_dissipation_at,
                    _cached_hashrate,
                ) = profile

                hardware_config = self.repository.get_hardware_config(hardware_id)
                if hardware_config is not None:
                    now = datetime.now(tz=timezone.utc)
                    heat_generated = self._apply_passive_dissipation(
                        heat_generated=heat_generated_stored,
                        dissipation_rate_per_minute=hardware_config.heat_dissipation_rate_per_minute,
                        last_dissipation_at=last_heat_dissipation_at,
                        now=now,
                    )

                    power_throttle_multiplier = self.hashrate_service.calculate_power_throttle_multiplier(
                        power_consumed,
                        power_capacity,
                    )
                    cooling_efficiency_multiplier = self.hashrate_service.calculate_cooling_efficiency_multiplier(
                        heat_generated,
                        cooling_capacity,
                    )
                    effective_hashrate = self.hashrate_service.calculate_effective_hashrate(
                        player_id=player_id,
                        hardware_config=hardware_config,
                        power_state=PowerState(
                            power_consumed=power_consumed,
                            power_capacity=power_capacity,
                        ),
                        cooling_state=CoolingState(
                            heat_generated=heat_generated,
                            cooling_capacity=cooling_capacity,
                        ),
                    )
                    self.repository.update_effective_hashrate_cache(
                        UUID(player_id),
                        effective_hashrate,
                        power_throttle_multiplier,
                        heat_generated,
                        cooling_efficiency_multiplier,
                        now,
                    )
                    return PlayerProfileResponse(
                        player_id=player_id,
                        hardware_id=hardware_config.hardware_id,
                        base_hashrate=hardware_config.base_hashrate,
                        power_available=self._calculate_power_available(
                            power_consumed=power_consumed,
                            power_capacity=power_capacity,
                        ),
                        power_consumed=power_consumed,
                        power_capacity=power_capacity,
                        power_throttle_multiplier=power_throttle_multiplier,
                        heat_generated=heat_generated,
                        cooling_capacity=cooling_capacity,
                        cooling_efficiency_multiplier=cooling_efficiency_multiplier,
                        last_heat_dissipation_at=now.isoformat(),
                        effective_hashrate=effective_hashrate,
                    )

        return self._default_profile(player_id=player_id)

    def assign_hardware_state(
        self,
        *,
        player_id: str,
        hardware_id: str | None = None,
        power_consumed: float | None = None,
        power_capacity: float | None = None,
        cooling_capacity: float | None = None,
    ) -> PlayerProfileResponse:
        resolved_power_consumed = power_consumed
        if hardware_id is not None and resolved_power_consumed is None:
            hardware_config = self.repository.get_hardware_config(hardware_id)
            if hardware_config is None:
                raise ValueError(f"Unknown hardware_id: {hardware_id}")
            resolved_power_consumed = hardware_config.base_power_consumption

        self.repository.update_profile_hardware_state(
            UUID(player_id),
            hardware_id=hardware_id,
            power_consumed=resolved_power_consumed,
            power_capacity=power_capacity,
            cooling_capacity=cooling_capacity,
        )
        return self.get_profile(player_id=player_id)

    def _default_profile(self, *, player_id: str | None = None) -> PlayerProfileResponse:
        hardware_config = HardwareConfig(
            hardware_id=DEFAULT_HARDWARE_ID,
            base_hashrate=DEFAULT_HASHRATE_HPS,
            base_power_consumption=DEFAULT_POWER_CONSUMED,
            heat_generation=DEFAULT_HEAT_GENERATED,
        )
        power_throttle_multiplier = DEFAULT_POWER_THROTTLE_MULTIPLIER
        heat_generated = self.hashrate_service.calculate_heat_generated(
            hardware_config.heat_generation,
            DEFAULT_POWER_CONSUMED,
            DEFAULT_POWER_CAPACITY,
        )
        cooling_efficiency_multiplier = self.hashrate_service.calculate_cooling_efficiency_multiplier(
            heat_generated,
            DEFAULT_COOLING_CAPACITY,
        )
        effective_hashrate = self.hashrate_service.calculate_effective_hashrate(
            player_id=player_id or DEFAULT_PLAYER_ID,
            hardware_config=hardware_config,
            power_state=PowerState(
                power_consumed=DEFAULT_POWER_CONSUMED,
                power_capacity=DEFAULT_POWER_CAPACITY,
            ),
            cooling_state=CoolingState(
                heat_generated=heat_generated,
                cooling_capacity=DEFAULT_COOLING_CAPACITY,
            ),
        )
        return PlayerProfileResponse(
            player_id=player_id or DEFAULT_PLAYER_ID,
            hardware_id=hardware_config.hardware_id,
            base_hashrate=hardware_config.base_hashrate,
            power_available=self._calculate_power_available(
                power_consumed=DEFAULT_POWER_CONSUMED,
                power_capacity=DEFAULT_POWER_CAPACITY,
            ),
            power_consumed=DEFAULT_POWER_CONSUMED,
            power_capacity=DEFAULT_POWER_CAPACITY,
            power_throttle_multiplier=power_throttle_multiplier,
            heat_generated=heat_generated,
            cooling_capacity=DEFAULT_COOLING_CAPACITY,
            cooling_efficiency_multiplier=cooling_efficiency_multiplier,
            last_heat_dissipation_at=None,
            effective_hashrate=effective_hashrate,
        )

    @staticmethod
    def _calculate_power_available(*, power_consumed: float, power_capacity: float) -> float:
        return max(0.0, power_capacity - power_consumed)

    @staticmethod
    def _apply_passive_dissipation(
        *,
        heat_generated: float,
        dissipation_rate_per_minute: float,
        last_dissipation_at: datetime | None,
        now: datetime | None = None,
    ) -> float:
        """Exponentially decay heat based on elapsed minutes since last dissipation.

        Uses: heat_after = heat_before × (1 - rate) ^ elapsed_minutes
        """
        if heat_generated <= 0.0 or last_dissipation_at is None:
            return heat_generated
        if dissipation_rate_per_minute <= 0.0:
            return heat_generated

        if now is None:
            now = datetime.now(tz=timezone.utc)
        if last_dissipation_at.tzinfo is None:
            last_dissipation_at = last_dissipation_at.replace(tzinfo=timezone.utc)

        elapsed_seconds = (now - last_dissipation_at).total_seconds()
        if elapsed_seconds <= 0.0:
            return heat_generated

        elapsed_minutes = elapsed_seconds / 60.0
        decay_factor = (1.0 - dissipation_rate_per_minute) ** elapsed_minutes
        return max(0.0, heat_generated * decay_factor)
