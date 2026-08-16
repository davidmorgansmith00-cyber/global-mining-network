from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


AMOUNT_QUANTIZE = Decimal("0.000001")


@dataclass(frozen=True)
class RewardSettlementConfig:
    base_block_reward: Decimal = Decimal("100")
    target_required_work: Decimal = Decimal("100")
    minimum_block_reward: Decimal = Decimal("1")


class RewardSettlementService:
    def __init__(self, config: RewardSettlementConfig | None = None) -> None:
        self.config = config or RewardSettlementConfig()

    def compute_block_reward(self, *, required_work: Decimal, total_work: Decimal) -> Decimal:
        del total_work
        if self.config.target_required_work <= 0:
            return self._quantize(self.config.base_block_reward)

        difficulty_scale = required_work / self.config.target_required_work
        scaled_reward = self.config.base_block_reward * difficulty_scale
        return self._quantize(max(scaled_reward, self.config.minimum_block_reward))

    def allocate_player_rewards(
        self,
        *,
        total_reward: Decimal,
        contributions_by_player: dict[str, Decimal],
    ) -> dict[str, Decimal]:
        total_contribution = sum(contributions_by_player.values(), Decimal("0"))
        if total_contribution <= 0:
            return {}

        unrounded: dict[str, Decimal] = {}
        rounded: dict[str, Decimal] = {}
        for player_id, contribution in contributions_by_player.items():
            share = total_reward * (contribution / total_contribution)
            unrounded[player_id] = share
            rounded[player_id] = self._quantize(share)

        rounded_sum = sum(rounded.values(), Decimal("0"))
        residual = self._quantize(total_reward - rounded_sum)
        step = AMOUNT_QUANTIZE

        if residual != Decimal("0"):
            if residual > 0:
                ordering = sorted(
                    contributions_by_player.keys(),
                    key=lambda pid: (contributions_by_player[pid], unrounded[pid], pid),
                    reverse=True,
                )
                while residual > 0:
                    for player_id in ordering:
                        if residual <= 0:
                            break
                        rounded[player_id] += step
                        residual -= step
            else:
                ordering = sorted(
                    contributions_by_player.keys(),
                    key=lambda pid: (contributions_by_player[pid], unrounded[pid], pid),
                )
                while residual < 0:
                    for player_id in ordering:
                        if residual >= 0:
                            break
                        if rounded[player_id] > 0:
                            rounded[player_id] -= step
                            residual += step

        return {player_id: self._quantize(amount) for player_id, amount in rounded.items() if amount > 0}

    @staticmethod
    def _quantize(value: Decimal) -> Decimal:
        return value.quantize(AMOUNT_QUANTIZE, rounding=ROUND_HALF_UP)
