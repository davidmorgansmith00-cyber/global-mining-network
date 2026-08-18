from pydantic import BaseModel


class StarterMachine(BaseModel):
    hardware_id: str
    name: str
    hashrate_hps: int


class BootstrapResponse(BaseModel):
    player_id: str
    starter_machine: StarterMachine


class PlayerProfileResponse(BaseModel):
    schema_version: str = "player.profile.v1.1"
    player_id: str
    hardware_id: str
    base_hashrate: float
    power_available: float
    power_capacity: float
    cooling_efficiency: float
    effective_hashrate: float