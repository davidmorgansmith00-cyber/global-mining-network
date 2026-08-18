from __future__ import annotations

from uuid import UUID

from domain.hardware.schemas import CoolingState, HardwareConfig, PowerState
from domain.hardware.service import GmnHardwareHashrateService
from domain.players.repository import PlayerRepository
from domain.players.schemas import BootstrapResponse, PlayerProfileResponse, StarterMachine
from shared.database import database_is_configured


DEFAULT_PLAYER_ID = "player_placeholder"
DEFAULT_HARDWARE_ID = "starter_rusty_home_computer"
DEFAULT_HARDWARE_NAME = "Rusty Home Computer"
DEFAULT_HASHRATE_HPS = 12.0
DEFAULT_POWER_AVAILABLE = 120.0
DEFAULT_POWER_CAPACITY = 120.0
DEFAULT_COOLING_EFFICIENCY = 1.0
DEFAULT_POWER_CONSUMPTION = 120.0
DEFAULT_HEAT_GENERATION = 40.0


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
                hardware_id, power_available, power_capacity, cooling_efficiency, _cached_hashrate = profile
                hardware_config = self.repository.get_hardware_config(hardware_id)
                if hardware_config is not None:
                    effective_hashrate = self.hashrate_service.calculate_effective_hashrate(
                        player_id=player_id,
                        hardware_config=hardware_config,
                        power_state=PowerState(
                            power_available=power_available,
                            power_capacity=power_capacity,
                        ),
                        cooling_state=CoolingState(cooling_efficiency=cooling_efficiency),
                    )
                    self.repository.update_effective_hashrate_cache(UUID(player_id), effective_hashrate)
                    return PlayerProfileResponse(
                        player_id=player_id,
                        hardware_id=hardware_config.hardware_id,
                        base_hashrate=hardware_config.base_hashrate,
                        power_available=power_available,
                        power_capacity=power_capacity,
                        cooling_efficiency=cooling_efficiency,
                        effective_hashrate=effective_hashrate,
                    )

        return self._default_profile(player_id=player_id)

    def assign_hardware_state(
        self,
        *,
        player_id: str,
        hardware_id: str | None = None,
        power_available: float | None = None,
        power_capacity: float | None = None,
        cooling_efficiency: float | None = None,
    ) -> PlayerProfileResponse:
        self.repository.update_profile_hardware_state(
            UUID(player_id),
            hardware_id=hardware_id,
            power_available=power_available,
            power_capacity=power_capacity,
            cooling_efficiency=cooling_efficiency,
        )
        return self.get_profile(player_id=player_id)

    def _default_profile(self, *, player_id: str | None = None) -> PlayerProfileResponse:
        hardware_config = HardwareConfig(
            hardware_id=DEFAULT_HARDWARE_ID,
            base_hashrate=DEFAULT_HASHRATE_HPS,
            base_power_consumption=DEFAULT_POWER_CONSUMPTION,
            heat_generation=DEFAULT_HEAT_GENERATION,
        )
        effective_hashrate = self.hashrate_service.calculate_effective_hashrate(
            player_id=player_id or DEFAULT_PLAYER_ID,
            hardware_config=hardware_config,
            power_state=PowerState(
                power_available=DEFAULT_POWER_AVAILABLE,
                power_capacity=DEFAULT_POWER_CAPACITY,
            ),
            cooling_state=CoolingState(cooling_efficiency=DEFAULT_COOLING_EFFICIENCY),
        )
        return PlayerProfileResponse(
            player_id=player_id or DEFAULT_PLAYER_ID,
            hardware_id=hardware_config.hardware_id,
            base_hashrate=hardware_config.base_hashrate,
            power_available=DEFAULT_POWER_AVAILABLE,
            power_capacity=DEFAULT_POWER_CAPACITY,
            cooling_efficiency=DEFAULT_COOLING_EFFICIENCY,
            effective_hashrate=effective_hashrate,
        )