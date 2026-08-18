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

    def calculate_cooling_efficiency_multiplier(self, heat_generated: float, cooling_capacity: float) -> float:
        """Return cooling efficiency multiplier (0.1–1.0) from heat vs cooling capacity.

        When heat_generated <= cooling_capacity the multiplier is 1.0 (no penalty).
        Above capacity a cubic-falloff curve applies down to a floor of 0.1, mirroring
        the power-throttle curve pattern.
        """
        heat = max(_to_decimal(heat_generated), _ZERO)
        capacity = _to_decimal(cooling_capacity)

        if capacity <= _ZERO:
            return float(_MIN_MULTIPLIER)
        if heat <= capacity:
            return float(_MAX_MULTIPLIER)

        excess_ratio = (heat - capacity) / capacity
        cubic_falloff = (excess_ratio * excess_ratio * excess_ratio).sqrt()
        return float(max(_MIN_MULTIPLIER, _MAX_MULTIPLIER - cubic_falloff))

    def calculate_heat_generated(
        self,
        base_heat_generation: float,
        power_consumed: float,
        power_capacity: float,
    ) -> float:
        """Compute heat emitted by hardware scaled by its power-consumption ratio.

        heat_generated = base_heat_generation × (power_consumed / power_capacity)
        Clamped to [0, base_heat_generation] so that over-capacity draw does not
        generate *more* heat than the hardware's rated maximum.
        """
        heat = max(_to_decimal(base_heat_generation), _ZERO)
        consumed = max(_to_decimal(power_consumed), _ZERO)
        capacity = _to_decimal(power_capacity)

        if capacity <= _ZERO:
            return float(heat.quantize(_HASHRATE_PRECISION, rounding=ROUND_HALF_UP))

        ratio = min(consumed / capacity, _MAX_MULTIPLIER)
        return float((heat * ratio).quantize(_HASHRATE_PRECISION, rounding=ROUND_HALF_UP))

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
        cooling_multiplier = _clamp(
            self.calculate_cooling_efficiency_multiplier(
                cooling_state.heat_generated,
                cooling_state.cooling_capacity,
            )
        )

        return float(
            (base_hashrate * power_multiplier * cooling_multiplier).quantize(
                _HASHRATE_PRECISION,
                rounding=ROUND_HALF_UP,
            )
        )
