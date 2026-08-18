from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import hashlib
import json
import math
from threading import Lock
from typing import Any, Callable
from uuid import uuid4

from shared.database import database_is_configured, open_connection

from domain.economy.parameters import EconomyParameterService, get_economy_parameter_service


@dataclass
class AbExperiment:
    experiment_id: str
    name: str
    cohort_a_params: dict[str, Any]
    cohort_b_params: dict[str, Any]
    start_at: datetime
    end_at: datetime
    status: str
    results: dict[str, Any]
    created_by_admin_id: str


class EconomyExperimentService:
    def __init__(
        self,
        *,
        parameter_service: EconomyParameterService | None = None,
        metrics_provider: Callable[[str], dict[str, Any]] | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self._parameter_service = parameter_service or get_economy_parameter_service()
        self._metrics_provider = metrics_provider or (lambda _player_id: {})
        self._now_provider = now_provider or (lambda: datetime.now(UTC))
        self._experiments: dict[str, AbExperiment] = {}
        self._assignments: dict[tuple[str, str], str] = {}
        self._lock = Lock()

    def create_experiment(
        self,
        name: str,
        params_a: dict[str, Any],
        params_b: dict[str, Any],
        duration_days: int,
        created_by_admin_id: str = "system",
    ) -> str:
        experiment_id = str(uuid4())
        now = self._now_provider()
        experiment = AbExperiment(
            experiment_id=experiment_id,
            name=name,
            cohort_a_params=dict(params_a),
            cohort_b_params=dict(params_b),
            start_at=now,
            end_at=now + timedelta(days=max(1, duration_days)),
            status="active",
            results={},
            created_by_admin_id=created_by_admin_id,
        )
        with self._lock:
            self._experiments[experiment_id] = experiment
        if database_is_configured():
            self._insert_experiment_db(experiment)
        return experiment_id

    def assign_player_to_cohort(self, player_id: str, experiment_id: str) -> str:
        key = (player_id, experiment_id)
        with self._lock:
            if key in self._assignments:
                return self._assignments[key]

            digest = hashlib.sha256(f"{player_id}:{experiment_id}".encode("utf-8")).digest()
            cohort = "a" if digest[0] % 2 == 0 else "b"
            self._assignments[key] = cohort
        if database_is_configured():
            self._insert_assignment_db(player_id, experiment_id, cohort)
        return cohort

    def get_player_parameters(self, player_id: str) -> dict[str, Any]:
        baseline = self._parameter_service.get_current_parameters().to_public_dict()
        now = self._now_provider()
        for experiment in self._experiments.values():
            if experiment.status != "active" or experiment.start_at > now or experiment.end_at < now:
                continue
            cohort = self.assign_player_to_cohort(player_id, experiment.experiment_id)
            overrides = experiment.cohort_a_params if cohort == "a" else experiment.cohort_b_params
            baseline.update(overrides)
        return baseline

    def analyze_experiment_results(self, experiment_id: str) -> dict[str, Any]:
        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            raise ValueError("experiment_not_found")

        cohort_players: dict[str, list[str]] = {"a": [], "b": []}
        with self._lock:
            assignment_snapshot = dict(self._assignments)
        for (player_id, exp_id), cohort in assignment_snapshot.items():
            if exp_id == experiment_id:
                cohort_players[cohort].append(player_id)

        cohort_stats = {
            "a": self._aggregate_cohort_stats(cohort_players["a"]),
            "b": self._aggregate_cohort_stats(cohort_players["b"]),
        }

        balances_a = cohort_stats["a"]["_balances"]
        balances_b = cohort_stats["b"]["_balances"]
        p_value = self._welch_t_p_value(balances_a, balances_b)
        significant = p_value < 0.05

        result = {
            "experiment_id": experiment_id,
            "name": experiment.name,
            "status": experiment.status,
            "cohort_a": self._public_stats(cohort_stats["a"]),
            "cohort_b": self._public_stats(cohort_stats["b"]),
            "p_value": round(p_value, 6),
            "statistically_significant": significant,
            "winner": self._pick_winner(cohort_stats["a"], cohort_stats["b"], significant),
        }
        with self._lock:
            experiment.results = result
            if self._now_provider() > experiment.end_at and experiment.status == "active":
                experiment.status = "completed"

        if database_is_configured():
            self._update_experiment_results_db(experiment)

        return result

    def promote_winning_cohort(self, experiment_id: str, cohort: str, admin_id: str = "system") -> dict[str, Any]:
        if cohort not in {"a", "b"}:
            raise ValueError("invalid_cohort")

        experiment = self._experiments.get(experiment_id)
        if experiment is None:
            raise ValueError("experiment_not_found")

        winning_params = experiment.cohort_a_params if cohort == "a" else experiment.cohort_b_params
        current = self._parameter_service.get_current_parameters()

        updated = self._parameter_service.set_parameters(
            difficulty_base=Decimal(str(winning_params.get("difficulty_base", current.difficulty_base))),
            reward_per_work_unit=Decimal(str(winning_params.get("reward_per_work_unit", current.reward_per_work_unit))),
            tier_unlock_times=winning_params.get("tier_unlock_times", current.tier_unlock_times),
            cosmetic_prices={
                k: Decimal(str(v))
                for k, v in winning_params.get("cosmetic_prices", current.cosmetic_prices).items()
            },
            battle_pass_price=Decimal(str(winning_params.get("battle_pass_price", current.battle_pass_price))),
            event_frequency=str(winning_params.get("event_frequency", current.event_frequency)),
            reason=f"experiment_promotion:{experiment_id}:{cohort}",
            admin_id=admin_id,
        )
        with self._lock:
            experiment.status = "completed"
        return updated.to_public_dict()

    def list_active_experiments(self) -> list[dict[str, Any]]:
        now = self._now_provider()
        active = []
        for experiment in self._experiments.values():
            if experiment.status == "active" and experiment.start_at <= now <= experiment.end_at:
                active.append(
                    {
                        "experiment_id": experiment.experiment_id,
                        "name": experiment.name,
                        "start_at": experiment.start_at.isoformat(),
                        "end_at": experiment.end_at.isoformat(),
                        "status": experiment.status,
                    }
                )
        return active

    def _aggregate_cohort_stats(self, players: list[str]) -> dict[str, Any]:
        if not players:
            return {
                "players": 0,
                "avg_player_balance": 0.0,
                "tier_distribution": {},
                "churn_rate": 0.0,
                "avg_spending": 0.0,
                "_balances": [],
            }

        balances: list[float] = []
        tier_distribution: dict[int, int] = {}
        churned = 0
        spending_total = 0.0

        for player_id in players:
            metrics = self._metrics_provider(player_id)
            balance = float(metrics.get("balance", 0.0))
            tier = int(metrics.get("tier", 1))
            churn_flag = bool(metrics.get("churned", False))
            spending = float(metrics.get("spending", 0.0))

            balances.append(balance)
            tier_distribution[tier] = tier_distribution.get(tier, 0) + 1
            if churn_flag:
                churned += 1
            spending_total += spending

        return {
            "players": len(players),
            "avg_player_balance": sum(balances) / len(balances),
            "tier_distribution": {f"tier_{tier}": count for tier, count in sorted(tier_distribution.items())},
            "churn_rate": churned / len(players),
            "avg_spending": spending_total / len(players),
            "_balances": balances,
        }

    @staticmethod
    def _public_stats(stats: dict[str, Any]) -> dict[str, Any]:
        return {
            "players": stats["players"],
            "avg_player_balance": round(float(stats["avg_player_balance"]), 6),
            "tier_distribution": stats["tier_distribution"],
            "churn_rate": round(float(stats["churn_rate"]), 6),
            "avg_spending": round(float(stats["avg_spending"]), 6),
        }

    @staticmethod
    def _pick_winner(stats_a: dict[str, Any], stats_b: dict[str, Any], significant: bool) -> str:
        if not significant:
            return "inconclusive"
        score_a = float(stats_a["avg_player_balance"]) - float(stats_a["churn_rate"] * 100)
        score_b = float(stats_b["avg_player_balance"]) - float(stats_b["churn_rate"] * 100)
        return "a" if score_a >= score_b else "b"

    @staticmethod
    def _welch_t_p_value(group_a: list[float], group_b: list[float]) -> float:
        if len(group_a) < 2 or len(group_b) < 2:
            return 1.0

        mean_a = sum(group_a) / len(group_a)
        mean_b = sum(group_b) / len(group_b)
        var_a = sum((x - mean_a) ** 2 for x in group_a) / (len(group_a) - 1)
        var_b = sum((x - mean_b) ** 2 for x in group_b) / (len(group_b) - 1)

        denom = math.sqrt((var_a / len(group_a)) + (var_b / len(group_b)))
        if denom == 0:
            return 1.0
        t_value = abs(mean_a - mean_b) / denom

        return min(1.0, math.erfc(t_value / math.sqrt(2)))

    def _insert_experiment_db(self, experiment: AbExperiment) -> None:
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ab_experiments (
                        experiment_id, name, cohort_a_params_json, cohort_b_params_json,
                        start_at, end_at, status, results_json, created_by_admin_id
                    )
                    VALUES (%s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        experiment.experiment_id,
                        experiment.name,
                        json.dumps(experiment.cohort_a_params),
                        json.dumps(experiment.cohort_b_params),
                        experiment.start_at,
                        experiment.end_at,
                        experiment.status,
                        json.dumps(experiment.results),
                        experiment.created_by_admin_id,
                    ),
                )
            conn.commit()

    def _insert_assignment_db(self, player_id: str, experiment_id: str, cohort: str) -> None:
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO experiment_cohort_assignment (player_id, experiment_id, cohort, assigned_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (player_id, experiment_id) DO NOTHING
                    """,
                    (player_id, experiment_id, cohort),
                )
            conn.commit()

    def _update_experiment_results_db(self, experiment: AbExperiment) -> None:
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE ab_experiments
                    SET status = %s,
                        results_json = %s::jsonb
                    WHERE experiment_id = %s
                    """,
                    (experiment.status, json.dumps(experiment.results), experiment.experiment_id),
                )
            conn.commit()


_experiment_service: EconomyExperimentService | None = None
_experiment_lock = Lock()


def get_economy_experiment_service() -> EconomyExperimentService:
    global _experiment_service
    if _experiment_service is None:
        with _experiment_lock:
            if _experiment_service is None:
                _experiment_service = EconomyExperimentService()
    return _experiment_service
