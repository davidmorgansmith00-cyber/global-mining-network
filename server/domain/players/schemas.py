from pydantic import BaseModel


class StarterMachine(BaseModel):
    hardware_id: str
    name: str
    hashrate_hps: int


class BootstrapResponse(BaseModel):
    player_id: str
    starter_machine: StarterMachine


class PlayerProfileResponse(BaseModel):
    schema_version: str = "player.profile.v1.3"
    player_id: str
    hardware_id: str
    base_hashrate: float
    power_available: float
    power_consumed: float
    power_capacity: float
    power_throttle_multiplier: float
    heat_generated: float
    cooling_capacity: float
    cooling_efficiency_multiplier: float
    last_heat_dissipation_at: str | None
    effective_hashrate: float