from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HardwareConfig:
    hardware_id: str
    base_hashrate: float
    base_power_consumption: float
    heat_generation: float


@dataclass(frozen=True)
class PowerState:
    power_consumed: float
    power_capacity: float


@dataclass(frozen=True)
class CoolingState:
    cooling_efficiency: float
