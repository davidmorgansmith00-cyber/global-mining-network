from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HardwareConfig:
    hardware_id: str
    base_hashrate: float
    base_power_consumption: float
    heat_generation: float
    heat_dissipation_rate_per_minute: float = 0.05


@dataclass(frozen=True)
class PowerState:
    power_consumed: float
    power_capacity: float


@dataclass(frozen=True)
class CoolingState:
    heat_generated: float
    cooling_capacity: float
