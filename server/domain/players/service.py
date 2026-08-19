from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from domain.hardware.schemas import CoolingState, HardwareConfig, PowerState
from domain.hardware.service import GmnHardwareHashrateService
from domain.hardware.upgrade_service import HardwareUpgradeService
from domain.mining.service import MiningSimulationService
from domain.market.service import NpcMarketService
from domain.players.repository import (
    DEFAULT_COOLING_CAPACITY,
    DEFAULT_COOLING_EFFICIENCY_MULTIPLIER,
    DEFAULT_HEAT_GENERATED,
    DEFAULT_POWER_CAPACITY,
    DEFAULT_POWER_CONSUMED,
    DEFAULT_POWER_THROTTLE_MULTIPLIER,
    PlayerRepository,
)
from domain.players.schemas import (
    BootstrapResponse,
    CurrentHardwareInfo,
    NextUpgradeRecommendation,
    PlayerProfileResponse,
    StarterMachine,
    UpgradeProgressionEntry,
)
from domain.telemetry.service import get_telemetry_service
from shared.database import database_is_configured


DEFAULT_PLAYER_ID = "player_placeholder"
DEFAULT_HARDWARE_ID = "starter_rusty_home_computer"
DEFAULT_HARDWARE_NAME = "Rusty Home Computer"
DEFAULT_HASHRATE_HPS = 12.0
TIER_ONE_CAP = Decimal("1000")
TIER_TWO_CAP = Decimal("5000")
TIER_THREE_CAP = Decimal("10000")


class PlayerProgressionService:
    def calculate_player_tier(self, blocks_finalized_count: int) -> int:
        if blocks_finalized_count >= 20:
            return 3
        if blocks_finalized_count >= 5:
            return 2
        return 1

    def get_offline_cap_for_tier(self, player_tier: int) -> Decimal:
        if player_tier <= 1:
            return TIER_ONE_CAP
        if player_tier == 2:
            return TIER_TWO_CAP
        if player_tier == 3:
            return TIER_THREE_CAP
        return TIER_THREE_CAP * (Decimal("2") ** (player_tier - 3))


class PlayerBootstrapService:
    def __init__(self) -> None:
        self.repository = PlayerRepository()

    def bootstrap(self, player_id: str | None = None) -> BootstrapResponse:
        if database_is_configured() and player_id is not None:
            profile = self.repository.get_profile(UUID(player_id))
            if profile is not None:
                hardware_id, name, hashrate_hps = profile
                return BootstrapResponse(
                    player_id=player_id,
                    starter_machine=StarterMachine(
                        hardware_id=hardware_id,
                        name=name,
                        hashrate_hps=hashrate_hps,
                    ),
                )

        return BootstrapResponse(
            player_id=player_id or DEFAULT_PLAYER_ID,
            starter_machine=StarterMachine(
                hardware_id=DEFAULT_HARDWARE_ID,
                name=DEFAULT_HARDWARE_NAME,
                hashrate_hps=int(DEFAULT_HASHRATE_HPS),
            ),
        )


class PlayerProfileService:
    def __init__(self) -> None:
        self.repository = PlayerRepository()
        self.hashrate_service = GmnHardwareHashrateService()
        self.progression_service = PlayerProgressionService()
        self.market_service = NpcMarketService()
        self.upgrade_service = HardwareUpgradeService()

    def get_profile(self, player_id: str | None = None) -> PlayerProfileResponse:
        if database_is_configured() and player_id is not None:
            player_uuid = UUID(player_id)
            blocks_finalized_contributed_count = self.repository.get_blocks_finalized_contributed_count(player_uuid)
            player_tier = self.calculate_player_tier(blocks_finalized_contributed_count)
            old_player_tier = self.repository.update_player_progression(
                player_uuid,
                blocks_finalized_contributed_count=blocks_finalized_contributed_count,
                player_tier=player_tier,
            )
            profile = self.repository.get_profile_state(UUID(player_id))
            if profile is not None:
                # Emit tier upgrade event (fire-and-forget) when tier increases
                if player_tier > old_player_tier:
                    try:
                        get_telemetry_service().emit_tier_upgraded(
                            player_id=player_id,
                            from_tier=old_player_tier,
                            to_tier=player_tier,
                            blocks_finalized_count=blocks_finalized_contributed_count,
                        )
                    except Exception:
                        pass  # telemetry must never affect player experience
                hardware_config = self.repository.get_hardware_config(profile.hardware_id)
                if hardware_config is not None:
                    now = datetime.now(tz=timezone.utc)
                    heat_generated = self._apply_passive_dissipation(
                        heat_generated=profile.heat_generated,
                        dissipation_rate_per_minute=hardware_config.heat_dissipation_rate_per_minute,
                        last_dissipation_at=profile.last_heat_dissipation_at,
                        now=now,
                    )

                    power_throttle_multiplier = self.hashrate_service.calculate_power_throttle_multiplier(
                        profile.power_consumed,
                        profile.power_capacity,
                    )
                    cooling_efficiency_multiplier = self.hashrate_service.calculate_cooling_efficiency_multiplier(
                        heat_generated,
                        profile.cooling_capacity,
                    )
                    effective_hashrate = self.hashrate_service.calculate_effective_hashrate(
                        player_id=player_id,
                        hardware_config=hardware_config,
                        power_state=PowerState(
                            power_consumed=profile.power_consumed,
                            power_capacity=profile.power_capacity,
                        ),
                        cooling_state=CoolingState(
                            heat_generated=heat_generated,
                            cooling_capacity=profile.cooling_capacity,
                        ),
                    )
                    current_offline_cap = self.get_offline_cap_for_tier(player_tier)
                    offline_progress = MiningSimulationService.simulate_offline_progress(
                        window_started_at=profile.last_offline_progress_at or now,
                        window_ended_at=now,
                        effective_hashrate_hps=Decimal(str(effective_hashrate)),
                        cap_limit=current_offline_cap,
                        offline_cap_tier=player_tier,
                    )
                    elapsed_offline_seconds = int(
                        (offline_progress.window_ended_at - offline_progress.window_started_at).total_seconds()
                    )
                    offline_ledger_entry: dict[str, object] | None = None
                    next_last_offline_progress_at: datetime | None = None
                    if elapsed_offline_seconds > 0:
                        next_last_offline_progress_at = now
                    if elapsed_offline_seconds > 0 and offline_progress.simulated_work > Decimal("0"):
                        offline_ledger_entry = {
                            "player_id": player_id,
                            "credited_work": offline_progress.credited_work,
                            "simulated_work": offline_progress.simulated_work,
                            "contribution_hashes": offline_progress.credited_work,
                            "cap_applied": offline_progress.cap_applied,
                            "cap_amount": offline_progress.cap_amount,
                            "offline_cap_tier": offline_progress.offline_cap_tier,
                            "cap_limit": offline_progress.cap_limit,
                            "window_started_at": offline_progress.window_started_at,
                            "window_ended_at": offline_progress.window_ended_at,
                            "posted_at": now,
                        }
                        try:
                            get_telemetry_service().emit_offline_progress(
                                player_id=player_id,
                                offline_duration_seconds=elapsed_offline_seconds,
                                work_credited=offline_progress.credited_work,
                                cap_applied=offline_progress.cap_applied,
                                offline_cap_tier=offline_progress.offline_cap_tier,
                            )
                        except Exception:
                            pass  # telemetry must never affect player experience
                    self.repository.update_effective_hashrate_cache(
                        player_uuid,
                        effective_hashrate,
                        power_throttle_multiplier,
                        heat_generated,
                        cooling_efficiency_multiplier,
                        now,
                        next_last_offline_progress_at,
                        profile.last_offline_progress_at,
                        offline_ledger_entry,
                    )
                    inventory = self.market_service.get_player_inventory(player_id)
                    available_for_purchase = [
                        item.model_dump()
                        for item in self.market_service.get_available_for_purchase(
                            player_id,
                            player_tier=player_tier,
                        )
                    ]
                    current_balance = self.market_service.get_player_reward_balance(player_id)
                    owned_hardware_ids = {
                        entry["item_id"]
                        for entry in inventory
                        if entry.get("item_type") == "hardware_upgrade"
                    }
                    current_hardware, next_recommended, progression = self._build_upgrade_fields(
                        current_hardware_id=hardware_config.hardware_id,
                        effective_hashrate=effective_hashrate,
                        current_offline_cap=current_offline_cap,
                        player_tier=player_tier,
                        current_balance=current_balance,
                        owned_hardware_ids=owned_hardware_ids,
                    )
                    return PlayerProfileResponse(
                        player_id=player_id,
                        hardware_id=hardware_config.hardware_id,
                        base_hashrate=hardware_config.base_hashrate,
                        power_available=self._calculate_power_available(
                            power_consumed=profile.power_consumed,
                            power_capacity=profile.power_capacity,
                        ),
                        power_consumed=profile.power_consumed,
                        power_capacity=profile.power_capacity,
                        power_throttle_multiplier=power_throttle_multiplier,
                        heat_generated=heat_generated,
                        cooling_capacity=profile.cooling_capacity,
                        cooling_efficiency_multiplier=cooling_efficiency_multiplier,
                        last_heat_dissipation_at=now.isoformat(),
                        effective_hashrate=effective_hashrate,
                        player_tier=player_tier,
                        blocks_finalized_contributed_count=blocks_finalized_contributed_count,
                        current_offline_cap=current_offline_cap,
                        offline_work_earned=offline_progress.credited_work,
                        offline_cap_applied=offline_progress.cap_applied,
                        offline_cap_amount=offline_progress.cap_amount,
                        offline_cap_status_message=self._format_offline_cap_status_message(
                            credited_work=offline_progress.credited_work,
                            cap_limit=offline_progress.cap_limit,
                            player_tier=offline_progress.offline_cap_tier,
                            cap_applied=offline_progress.cap_applied,
                        ),
                        inventory=inventory,
                        available_for_purchase=available_for_purchase,
                        current_hardware=current_hardware,
                        next_recommended_upgrade=next_recommended,
                        upgrade_progression=progression,
                        reward_balance=current_balance,
                    )

        return self._default_profile(player_id=player_id)

    def assign_hardware_state(
        self,
        *,
        player_id: str,
        hardware_id: str | None = None,
        power_consumed: float | None = None,
        power_capacity: float | None = None,
        cooling_capacity: float | None = None,
    ) -> PlayerProfileResponse:
        resolved_power_consumed = power_consumed
        if hardware_id is not None and resolved_power_consumed is None:
            hardware_config = self.repository.get_hardware_config(hardware_id)
            if hardware_config is None:
                raise ValueError(f"Unknown hardware_id: {hardware_id}")
            resolved_power_consumed = hardware_config.base_power_consumption

        self.repository.update_profile_hardware_state(
            UUID(player_id),
            hardware_id=hardware_id,
            power_consumed=resolved_power_consumed,
            power_capacity=power_capacity,
            cooling_capacity=cooling_capacity,
        )
        return self.get_profile(player_id=player_id)

    def calculate_player_tier(self, blocks_finalized_count: int) -> int:
        return self.progression_service.calculate_player_tier(blocks_finalized_count)

    def get_offline_cap_for_tier(self, player_tier: int) -> Decimal:
        return self.progression_service.get_offline_cap_for_tier(player_tier)

    def _default_profile(self, *, player_id: str | None = None) -> PlayerProfileResponse:
        hardware_config = HardwareConfig(
            hardware_id=DEFAULT_HARDWARE_ID,
            base_hashrate=DEFAULT_HASHRATE_HPS,
            base_power_consumption=DEFAULT_POWER_CONSUMED,
            heat_generation=DEFAULT_HEAT_GENERATED,
        )
        power_throttle_multiplier = DEFAULT_POWER_THROTTLE_MULTIPLIER
        heat_generated = self.hashrate_service.calculate_heat_generated(
            hardware_config.heat_generation,
            DEFAULT_POWER_CONSUMED,
            DEFAULT_POWER_CAPACITY,
        )
        cooling_efficiency_multiplier = self.hashrate_service.calculate_cooling_efficiency_multiplier(
            heat_generated,
            DEFAULT_COOLING_CAPACITY,
        )
        effective_hashrate = self.hashrate_service.calculate_effective_hashrate(
            player_id=player_id or DEFAULT_PLAYER_ID,
            hardware_config=hardware_config,
            power_state=PowerState(
                power_consumed=DEFAULT_POWER_CONSUMED,
                power_capacity=DEFAULT_POWER_CAPACITY,
            ),
            cooling_state=CoolingState(
                heat_generated=heat_generated,
                cooling_capacity=DEFAULT_COOLING_CAPACITY,
            ),
        )
        current_offline_cap = self.get_offline_cap_for_tier(1)
        current_hardware, next_recommended, progression = self._build_upgrade_fields(
            current_hardware_id=DEFAULT_HARDWARE_ID,
            effective_hashrate=effective_hashrate,
            current_offline_cap=current_offline_cap,
            player_tier=1,
            current_balance=Decimal("0"),
            owned_hardware_ids=set(),
        )
        return PlayerProfileResponse(
            player_id=player_id or DEFAULT_PLAYER_ID,
            hardware_id=hardware_config.hardware_id,
            base_hashrate=hardware_config.base_hashrate,
            power_available=self._calculate_power_available(
                power_consumed=DEFAULT_POWER_CONSUMED,
                power_capacity=DEFAULT_POWER_CAPACITY,
            ),
            power_consumed=DEFAULT_POWER_CONSUMED,
            power_capacity=DEFAULT_POWER_CAPACITY,
            power_throttle_multiplier=power_throttle_multiplier,
            heat_generated=heat_generated,
            cooling_capacity=DEFAULT_COOLING_CAPACITY,
            cooling_efficiency_multiplier=cooling_efficiency_multiplier,
            last_heat_dissipation_at=None,
            effective_hashrate=effective_hashrate,
            player_tier=1,
            blocks_finalized_contributed_count=0,
            current_offline_cap=current_offline_cap,
            offline_work_earned=Decimal("0"),
            offline_cap_applied=False,
            offline_cap_amount=Decimal("0"),
            offline_cap_status_message=self._format_offline_cap_status_message(
                credited_work=Decimal("0"),
                cap_limit=current_offline_cap,
                player_tier=1,
                cap_applied=False,
            ),
            inventory=[],
            available_for_purchase=[],
            current_hardware=current_hardware,
            next_recommended_upgrade=next_recommended,
            upgrade_progression=progression,
            reward_balance=Decimal("0"),
        )

    def _build_upgrade_fields(
        self,
        *,
        current_hardware_id: str,
        effective_hashrate: float,
        current_offline_cap: Decimal,
        player_tier: int,
        current_balance: Decimal,
        owned_hardware_ids: set[str],
    ) -> tuple[
        CurrentHardwareInfo | None,
        NextUpgradeRecommendation | None,
        list[UpgradeProgressionEntry],
    ]:
        hw_def = self.upgrade_service.get_definition(current_hardware_id)
        current_hardware: CurrentHardwareInfo | None = None
        if hw_def is not None:
            current_hardware = CurrentHardwareInfo(
                hardware_id=hw_def.hardware_id,
                name=hw_def.name,
                tier=hw_def.tier,
                base_hashrate=hw_def.base_hashrate,
                base_power_consumption=hw_def.base_power_consumption,
                base_heat_generation=hw_def.base_heat_generation,
                market_price=hw_def.market_price,
            )

        recommendation = self.upgrade_service.get_next_upgrade_recommendation(
            current_hardware_id=current_hardware_id,
            effective_hashrate=effective_hashrate,
            offline_cap_per_day=current_offline_cap,
            player_tier=player_tier,
            current_balance=current_balance,
        )
        next_recommended: NextUpgradeRecommendation | None = None
        if recommendation is not None:
            next_recommended = NextUpgradeRecommendation(
                hardware_id=recommendation.hardware_id,
                name=recommendation.name,
                tier=recommendation.tier,
                base_hashrate_improvement_pct=recommendation.base_hashrate_improvement_pct,
                cost=recommendation.cost,
                eta_seconds=recommendation.eta_seconds,
                unlock_blocked=recommendation.unlock_blocked,
            )

        raw_progression = self.upgrade_service.get_upgrade_progression(
            current_hardware_id=current_hardware_id,
            owned_hardware_ids=owned_hardware_ids,
            player_tier=player_tier,
        )
        progression = [
            UpgradeProgressionEntry(
                hardware_id=entry.hardware_id,
                name=entry.name,
                tier=entry.tier,
                market_price=entry.market_price,
                is_current=entry.is_current,
                is_owned=entry.is_owned,
                is_unlocked=entry.is_unlocked,
                unlock_condition=entry.unlock_condition,
            )
            for entry in raw_progression
        ]
        return current_hardware, next_recommended, progression

    @staticmethod
    def _calculate_power_available(*, power_consumed: float, power_capacity: float) -> float:
        return max(0.0, power_capacity - power_consumed)

    @staticmethod
    def _apply_passive_dissipation(
        *,
        heat_generated: float,
        dissipation_rate_per_minute: float,
        last_dissipation_at: datetime | None,
        now: datetime | None = None,
    ) -> float:
        """Exponentially decay heat based on elapsed minutes since last dissipation.

        Uses: heat_after = heat_before × (1 - rate) ^ elapsed_minutes
        """
        if heat_generated <= 0.0 or last_dissipation_at is None:
            return heat_generated
        if dissipation_rate_per_minute <= 0.0:
            return heat_generated

        if now is None:
            now = datetime.now(tz=timezone.utc)
        if last_dissipation_at.tzinfo is None:
            last_dissipation_at = last_dissipation_at.replace(tzinfo=timezone.utc)

        elapsed_seconds = (now - last_dissipation_at).total_seconds()
        if elapsed_seconds <= 0.0:
            return heat_generated

        elapsed_minutes = elapsed_seconds / 60.0
        decay_factor = (1.0 - dissipation_rate_per_minute) ** elapsed_minutes
        return max(0.0, heat_generated * decay_factor)

    @staticmethod
    def _format_offline_cap_status_message(
        *,
        credited_work: Decimal,
        cap_limit: Decimal,
        player_tier: int,
        cap_applied: bool,
    ) -> str:
        if cap_applied:
            return f"Offline work earned: {credited_work} (your tier allows {cap_limit})"
        return f"Offline work earned: {credited_work} of {cap_limit} (tier: {player_tier})"
