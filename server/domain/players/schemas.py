from decimal import Decimal

from pydantic import BaseModel


class StarterMachine(BaseModel):
    hardware_id: str
    name: str
    hashrate_hps: int


class BootstrapResponse(BaseModel):
    player_id: str
    starter_machine: StarterMachine


class CurrentHardwareInfo(BaseModel):
    hardware_id: str
    name: str
    tier: int
    base_hashrate: float
    base_power_consumption: float
    base_heat_generation: float
    market_price: Decimal


class NextUpgradeRecommendation(BaseModel):
    hardware_id: str
    name: str
    tier: int
    base_hashrate_improvement_pct: float
    cost: Decimal
    eta_seconds: int
    unlock_blocked: bool


class UpgradeProgressionEntry(BaseModel):
    hardware_id: str
    name: str
    tier: int
    market_price: Decimal
    is_current: bool
    is_owned: bool
    is_unlocked: bool
    unlock_condition: str | None


class PlayerProfileResponse(BaseModel):
    schema_version: str = "player.profile.v1.6"
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
    player_tier: int
    blocks_finalized_contributed_count: int
    current_offline_cap: Decimal
    offline_work_earned: Decimal
    offline_cap_applied: bool
    offline_cap_amount: Decimal
    offline_cap_status_message: str
    inventory: list[dict[str, object]]
    available_for_purchase: list[dict[str, object]]
    current_hardware: CurrentHardwareInfo | None
    next_recommended_upgrade: NextUpgradeRecommendation | None
    upgrade_progression: list[UpgradeProgressionEntry]