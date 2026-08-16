from pydantic import BaseModel


class StarterMachine(BaseModel):
    hardware_id: str
    name: str
    hashrate_hps: int


class BootstrapResponse(BaseModel):
    player_id: str
    starter_machine: StarterMachine