from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

HARDWARE_DEFINITIONS_PATH = Path(__file__).resolve().parents[3] / "content" / "hardware_definitions.json"
REWARD_PER_HASH: Decimal = Decimal("1")
TIER_UNLOCK_PATTERN = re.compile(r"^\s*player_tier\s*>=\s*(\d+)\s*$")
SECONDS_PER_DAY = Decimal("86400")


@dataclass(frozen=True)
class HardwareTierDefinition:
    hardware_id: str
    tier: int
    name: str
    description: str
    base_hashrate: float
    base_power_consumption: float
    base_heat_generation: float
    heat_dissipation_rate_per_minute: float
    market_price: Decimal
    unlock_condition: str | None
    previous_tier: str | None
    next_tier: str | None


@dataclass(frozen=True)
class UpgradeRecommendation:
    hardware_id: str
    name: str
    tier: int
    base_hashrate_improvement_pct: float
    cost: Decimal
    eta_seconds: int
    unlock_blocked: bool


@dataclass(frozen=True)
class UpgradeProgressionEntry:
    hardware_id: str
    name: str
    tier: int
    market_price: Decimal
    is_current: bool
    is_owned: bool
    is_unlocked: bool
    unlock_condition: str | None


class HardwareUpgradeService:
    def __init__(self) -> None:
        self._definitions_cache: dict[str, HardwareTierDefinition] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_all_tier_definitions(self) -> list[HardwareTierDefinition]:
        """Return hardware tier definitions sorted by tier ascending."""
        return sorted(self._load_definitions().values(), key=lambda d: d.tier)

    def get_definition(self, hardware_id: str) -> HardwareTierDefinition | None:
        return self._load_definitions().get(hardware_id)

    def is_hardware_tier_upgrade(self, item_id: str) -> bool:
        """Return True if item_id maps to a purchasable hardware tier (tier >= 2)."""
        definition = self._load_definitions().get(item_id)
        return definition is not None and definition.tier >= 2

    def calculate_eta_to_upgrade(
        self,
        *,
        effective_hashrate: float,
        upgrade_cost: Decimal,
        offline_cap_per_day: Decimal,
    ) -> int:
        """Return estimated seconds until player can afford the upgrade.

        Uses a conservative estimate: assume player earns at the offline cap rate
        (no online bonuses).  Returns 0 if the player can already afford it.

        effective_hashrate is kept as a parameter to allow future hashrate-weighted
        ETA refinements but the current calculation uses offline_cap_per_day directly.
        """
        del effective_hashrate  # reserved for future hashrate-weighted model
        if upgrade_cost <= Decimal("0"):
            return 0
        if offline_cap_per_day <= Decimal("0"):
            return int(10**9)  # practically unreachable

        expected_daily_earnings = offline_cap_per_day * REWARD_PER_HASH
        if expected_daily_earnings <= Decimal("0"):
            return int(10**9)

        days_to_upgrade = upgrade_cost / expected_daily_earnings
        return int((days_to_upgrade * SECONDS_PER_DAY).to_integral_value())

    def get_next_upgrade_recommendation(
        self,
        *,
        current_hardware_id: str,
        effective_hashrate: float,
        offline_cap_per_day: Decimal,
        player_tier: int,
        current_balance: Decimal,
    ) -> UpgradeRecommendation | None:
        """Return the next tier recommendation, or None if player is at max tier."""
        definition = self._load_definitions().get(current_hardware_id)
        if definition is None or definition.next_tier is None:
            # Not in the tier tree or already at max — look for any tier above current
            next_def = self._find_next_tier_above(current_hardware_id)
            if next_def is None:
                return None
        else:
            next_def = self._load_definitions().get(definition.next_tier)
            if next_def is None:
                return None

        remaining_cost = max(Decimal("0"), next_def.market_price - current_balance)
        eta_seconds = self.calculate_eta_to_upgrade(
            effective_hashrate=effective_hashrate,
            upgrade_cost=remaining_cost,
            offline_cap_per_day=offline_cap_per_day,
        )
        unlock_blocked = not self._is_unlocked(next_def, player_tier)

        current_def = self._load_definitions().get(current_hardware_id)
        current_hr = current_def.base_hashrate if current_def is not None else 0.0
        improvement_pct = (
            ((next_def.base_hashrate - current_hr) / current_hr * 100.0)
            if current_hr > 0.0
            else 0.0
        )
        return UpgradeRecommendation(
            hardware_id=next_def.hardware_id,
            name=next_def.name,
            tier=next_def.tier,
            base_hashrate_improvement_pct=round(improvement_pct, 2),
            cost=next_def.market_price,
            eta_seconds=eta_seconds,
            unlock_blocked=unlock_blocked,
        )

    def get_upgrade_progression(
        self,
        *,
        current_hardware_id: str,
        owned_hardware_ids: set[str],
        player_tier: int,
    ) -> list[UpgradeProgressionEntry]:
        """Return ordered progression tree with unlock/ownership status per tier."""
        entries = []
        for definition in self.get_all_tier_definitions():
            is_unlocked = self._is_unlocked(definition, player_tier)
            entries.append(
                UpgradeProgressionEntry(
                    hardware_id=definition.hardware_id,
                    name=definition.name,
                    tier=definition.tier,
                    market_price=definition.market_price,
                    is_current=definition.hardware_id == current_hardware_id,
                    is_owned=definition.hardware_id in owned_hardware_ids
                    or definition.hardware_id == current_hardware_id,
                    is_unlocked=is_unlocked,
                    unlock_condition=definition.unlock_condition,
                )
            )
        return entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_definitions(self) -> dict[str, HardwareTierDefinition]:
        if self._definitions_cache is not None:
            return self._definitions_cache

        data = json.loads(HARDWARE_DEFINITIONS_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("hardware_definitions_must_be_array")

        definitions: dict[str, HardwareTierDefinition] = {}
        for entry in data:
            if not isinstance(entry, dict):
                raise ValueError("hardware_definition_item_must_be_object")

            hardware_id = str(entry.get("hardware_id", "")).strip()
            if not hardware_id:
                raise ValueError("hardware_id_required")
            if hardware_id in definitions:
                raise ValueError(f"duplicate_hardware_id:{hardware_id}")

            tier = entry.get("tier")
            if not isinstance(tier, int) or tier < 1:
                raise ValueError(f"invalid_tier:{hardware_id}")

            for field in ("base_hashrate", "base_power_consumption", "base_heat_generation"):
                val = entry.get(field)
                if not isinstance(val, (int, float)) or val <= 0:
                    raise ValueError(f"invalid_{field}:{hardware_id}")

            try:
                market_price = Decimal(str(entry.get("market_price", "0")))
            except (InvalidOperation, TypeError):
                raise ValueError(f"invalid_market_price:{hardware_id}") from None
            if market_price < Decimal("0"):
                raise ValueError(f"negative_market_price:{hardware_id}")

            unlock_condition = entry.get("unlock_condition")
            if unlock_condition is not None:
                unlock_condition = str(unlock_condition).strip()
                if unlock_condition and TIER_UNLOCK_PATTERN.match(unlock_condition) is None:
                    raise ValueError(f"unsupported_unlock_condition:{hardware_id}")
                if not unlock_condition:
                    unlock_condition = None

            definitions[hardware_id] = HardwareTierDefinition(
                hardware_id=hardware_id,
                tier=tier,
                name=str(entry.get("name", "")).strip(),
                description=str(entry.get("description", "")).strip(),
                base_hashrate=float(entry["base_hashrate"]),
                base_power_consumption=float(entry["base_power_consumption"]),
                base_heat_generation=float(entry["base_heat_generation"]),
                heat_dissipation_rate_per_minute=float(entry.get("heat_dissipation_rate_per_minute", 0.05)),
                market_price=market_price.quantize(Decimal("0.000001")),
                unlock_condition=unlock_condition,
                previous_tier=entry.get("previous_tier"),
                next_tier=entry.get("next_tier"),
            )

        self._definitions_cache = definitions
        return definitions

    def _is_unlocked(self, definition: HardwareTierDefinition, player_tier: int) -> bool:
        if not definition.unlock_condition:
            return True
        match = TIER_UNLOCK_PATTERN.match(definition.unlock_condition)
        if match is None:
            return False
        return player_tier >= int(match.group(1))

    def _find_next_tier_above(self, current_hardware_id: str) -> HardwareTierDefinition | None:
        """Fallback: find lowest tier > current hardware's tier."""
        definitions = self._load_definitions()
        current_def = definitions.get(current_hardware_id)
        current_tier = current_def.tier if current_def is not None else 0
        candidates = [d for d in definitions.values() if d.tier > current_tier]
        if not candidates:
            return None
        return min(candidates, key=lambda d: d.tier)
