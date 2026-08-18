from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Union

from domain.hardware.schemas import CoolingState, HardwareConfig, PowerState


_HASHRATE_PRECISION = Decimal("0.000001")
_MAX_MULTIPLIER = Decimal("1.0")
_MIN_MULTIPLIER = Decimal("0.1")
_ZERO = Decimal("0")


def _to_decimal(value: Union[float, Decimal]) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _clamp(value: Union[float, Decimal]) -> Decimal:
    decimal_value = _to_decimal(value)
    if decimal_value < _ZERO:
        return _ZERO
    if decimal_value > _MAX_MULTIPLIER:
        return _MAX_MULTIPLIER
    return decimal_value


class GmnHardwareHashrateService:
    def calculate_power_throttle_multiplier(self, power_consumed: float, power_capacity: float) -> float:
        consumed = max(_to_decimal(power_consumed), _ZERO)
        capacity = _to_decimal(power_capacity)

        if consumed == _ZERO:
            return float(_MAX_MULTIPLIER)
        if capacity <= _ZERO:
            return float(_MIN_MULTIPLIER)
        if consumed <= capacity:
            return float(_MAX_MULTIPLIER)

        excess_ratio = (consumed - capacity) / capacity
        cubic_falloff = (excess_ratio * excess_ratio * excess_ratio).sqrt()
        return float(max(_MIN_MULTIPLIER, _MAX_MULTIPLIER - cubic_falloff))

    def calculate_effective_hashrate(
        self,
        player_id: str,
        hardware_config: HardwareConfig,
        power_state: PowerState,
        cooling_state: CoolingState,
    ) -> float:
        del player_id

        base_hashrate = max(_to_decimal(hardware_config.base_hashrate), Decimal("0"))
        power_multiplier = _clamp(
            self.calculate_power_throttle_multiplier(
                power_state.power_consumed,
                power_state.power_capacity,
            )
        )
        cooling_multiplier = _clamp(cooling_state.cooling_efficiency)

        return float(
            (base_hashrate * power_multiplier * cooling_multiplier).quantize(
                _HASHRATE_PRECISION,
                rounding=ROUND_HALF_UP,
            )
        )
