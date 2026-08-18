from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from domain.hardware.schemas import CoolingState, HardwareConfig, PowerState


_HASHRATE_PRECISION = Decimal("0.000001")


def _to_decimal(value: float) -> Decimal:
    return Decimal(str(value))


def _clamp(value: float) -> Decimal:
    decimal_value = _to_decimal(value)
    if decimal_value < 0:
        return Decimal("0")
    if decimal_value > 1:
        return Decimal("1")
    return decimal_value


class GmnHardwareHashrateService:
    def calculate_effective_hashrate(
        self,
        player_id: str,
        hardware_config: HardwareConfig,
        power_state: PowerState,
        cooling_state: CoolingState,
    ) -> float:
        del player_id

        base_hashrate = max(_to_decimal(hardware_config.base_hashrate), Decimal("0"))
        if power_state.power_capacity <= 0:
            power_multiplier = Decimal("0")
        else:
            power_multiplier = _clamp(power_state.power_available / power_state.power_capacity)
        cooling_multiplier = _clamp(cooling_state.cooling_efficiency)

        return float(
            (base_hashrate * power_multiplier * cooling_multiplier).quantize(
                _HASHRATE_PRECISION,
                rounding=ROUND_HALF_UP,
            )
        )

