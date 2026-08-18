from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from statistics import median
from typing import Any

from shared.database import database_is_configured, open_connection

from domain.economy.parameters import EconomyParameterService, get_economy_parameter_service


@dataclass(frozen=True)
class TuningRecommendation:
    parameter: str
    current_value: str
    suggested_value: str
    rationale: str


class EconomyAnalyzer:
    def __init__(
        self,
        *,
        parameter_service: EconomyParameterService | None = None,
        now_provider: callable | None = None,
        player_tiers: dict[str, int] | None = None,
        player_last_active: dict[str, datetime] | None = None,
        ledger_entries: list[dict[str, Any]] | None = None,
    ) -> None:
        self._parameter_service = parameter_service or get_economy_parameter_service()
        self._now_provider = now_provider or (lambda: datetime.now(UTC))
        self._player_tiers = player_tiers or {}
        self._player_last_active = player_last_active or {}
        self._ledger_entries = ledger_entries or []

    def analyze_progression_distribution(self) -> dict[str, Any]:
        tiers = self._load_player_tiers()
        histogram = {f"tier_{i}": 0 for i in range(1, 11)}
        if not tiers:
            return {
                "histogram": histogram,
                "percentiles": {"p50": 0, "p75": 0, "p90": 0},
                "median_tier": 0,
                "total_players": 0,
            }

        values = sorted(max(1, min(10, int(v))) for v in tiers.values())
        for value in values:
            histogram[f"tier_{value}"] += 1

        def _p(percent: float) -> int:
            idx = min(len(values) - 1, max(0, int(round((len(values) - 1) * percent))))
            return values[idx]

        return {
            "histogram": histogram,
            "percentiles": {"p50": _p(0.50), "p75": _p(0.75), "p90": _p(0.90)},
            "median_tier": int(median(values)),
            "total_players": len(values),
        }

    def analyze_spending_patterns(self) -> dict[str, Any]:
        spend_by_player = defaultdict(lambda: Decimal("0"))
        engagement_by_player = defaultdict(lambda: Decimal("0"))

        for entry in self._load_ledger_entries():
            entry_type = str(entry.get("entry_type", ""))
            amount = Decimal(str(entry.get("amount", "0")))
            player_id = str(entry.get("player_id", ""))
            if player_id == "":
                continue
            if amount < 0 and (entry_type.startswith("market.") or entry_type.startswith("hardware.")):
                spend_by_player[player_id] += -amount
            sessions = Decimal(str(entry.get("sessions", "0")))
            engagement_by_player[player_id] += sessions

        if not spend_by_player:
            return {
                "avg_spend_per_player": "0",
                "top_10_percent_spend": "0",
                "engagement_correlation": 0.0,
            }

        spends = sorted(spend_by_player.values())
        avg_spend = sum(spends, Decimal("0")) / Decimal(len(spends))
        top_count = max(1, int(len(spends) * 0.10))
        top_spend = sum(spends[-top_count:], Decimal("0"))

        players = list(spend_by_player.keys())
        spend_floats = [float(spend_by_player[p]) for p in players]
        engage_floats = [float(engagement_by_player[p]) for p in players]
        correlation = self._pearson(spend_floats, engage_floats)

        return {
            "avg_spend_per_player": str(avg_spend.quantize(Decimal("0.000001"))),
            "top_10_percent_spend": str(top_spend.quantize(Decimal("0.000001"))),
            "engagement_correlation": correlation,
        }

    def calculate_churn_rate(self, days: int = 7) -> dict[str, Any]:
        last_active = self._load_player_last_active()
        if not last_active:
            return {"days": days, "inactive_players": 0, "total_players": 0, "churn_rate_percent": 0.0}

        cutoff = self._now_provider() - timedelta(days=days)
        inactive = sum(1 for value in last_active.values() if value < cutoff)
        churn = (inactive / len(last_active)) * 100
        return {
            "days": days,
            "inactive_players": inactive,
            "total_players": len(last_active),
            "churn_rate_percent": round(churn, 4),
        }

    def calculate_inflation_rate(self, days: int = 1) -> dict[str, Any]:
        now = self._now_provider()
        window_start = now - timedelta(days=days)
        previous_window_start = window_start - timedelta(days=days)

        entries = self._load_ledger_entries()
        current_window_delta = Decimal("0")
        previous_window_delta = Decimal("0")

        for entry in entries:
            if str(entry.get("currency", "credits")) != "credits":
                continue
            amount = Decimal(str(entry.get("amount", "0")))
            created_at = entry.get("created_at")
            if not isinstance(created_at, datetime):
                continue
            if created_at >= window_start:
                current_window_delta += amount
            elif previous_window_start <= created_at < window_start:
                previous_window_delta += amount

        if previous_window_delta == 0:
            inflation = 0.0 if current_window_delta == 0 else 100.0
        else:
            inflation = float(((current_window_delta - previous_window_delta) / abs(previous_window_delta)) * Decimal("100"))

        return {
            "days": days,
            "current_window_delta": str(current_window_delta.quantize(Decimal("0.000001"))),
            "previous_window_delta": str(previous_window_delta.quantize(Decimal("0.000001"))),
            "inflation_rate_percent": round(inflation, 4),
        }

    def analyze_price_trends(self, item_id: str, days: int = 30) -> dict[str, Any]:
        cutoff = self._now_provider() - timedelta(days=days)
        prices: list[Decimal] = []
        for entry in self._load_ledger_entries():
            if str(entry.get("item_id", "")) != item_id:
                continue
            created_at = entry.get("created_at")
            if not isinstance(created_at, datetime) or created_at < cutoff:
                continue
            quantity = Decimal(str(entry.get("quantity", "0")))
            total_cost = Decimal(str(entry.get("total_cost", "0")))
            if quantity > 0:
                prices.append((total_cost / quantity).quantize(Decimal("0.000001")))

        if not prices:
            return {"item_id": item_id, "days": days, "average_price": "0", "volatility": "0", "samples": 0}

        avg = sum(prices, Decimal("0")) / Decimal(len(prices))
        variance = sum((p - avg) ** 2 for p in prices) / Decimal(len(prices))
        volatility = variance.sqrt() if variance > 0 else Decimal("0")
        return {
            "item_id": item_id,
            "days": days,
            "average_price": str(avg.quantize(Decimal("0.000001"))),
            "volatility": str(volatility.quantize(Decimal("0.000001"))),
            "samples": len(prices),
        }

    def recommend_parameter_tuning(self) -> list[dict[str, str]]:
        params = self._parameter_service.get_current_parameters()
        churn = self.calculate_churn_rate(days=7)
        inflation = self.calculate_inflation_rate(days=1)
        progression = self.analyze_progression_distribution()

        recommendations: list[TuningRecommendation] = []
        churn_pct = float(churn["churn_rate_percent"])
        inflation_pct = float(inflation["inflation_rate_percent"])
        median_tier = int(progression["median_tier"])

        if churn_pct > 25.0:
            current = params.reward_per_work_unit
            suggested = (current * Decimal("1.05")).quantize(Decimal("0.000001"))
            recommendations.append(
                TuningRecommendation(
                    parameter="reward_per_work_unit",
                    current_value=str(current),
                    suggested_value=str(suggested),
                    rationale="7-day churn is high; increasing early rewards may improve retention.",
                )
            )

        if inflation_pct > 10.0:
            current = params.difficulty_base
            suggested = (current * Decimal("1.03")).quantize(Decimal("0.000001"))
            recommendations.append(
                TuningRecommendation(
                    parameter="difficulty_base",
                    current_value=str(current),
                    suggested_value=str(suggested),
                    rationale="Daily credit inflation is elevated; raise difficulty slightly to reduce issuance.",
                )
            )

        if median_tier <= 1:
            current = dict(params.tier_unlock_times)
            adjusted = {key: max(300, int(value * 0.9)) for key, value in current.items()}
            recommendations.append(
                TuningRecommendation(
                    parameter="tier_unlock_times",
                    current_value=str(current),
                    suggested_value=str(adjusted),
                    rationale="Median progression is low; shorten tier unlock times to smooth onboarding.",
                )
            )

        return [
            {
                "parameter": rec.parameter,
                "current_value": rec.current_value,
                "suggested_value": rec.suggested_value,
                "rationale": rec.rationale,
            }
            for rec in recommendations
        ]

    def _load_player_tiers(self) -> dict[str, int]:
        if not database_is_configured():
            return dict(self._player_tiers)

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT player_id::text, COALESCE(player_tier, 1) FROM players")
                rows = cur.fetchall()
        return {str(row[0]): int(row[1]) for row in rows}

    def _load_player_last_active(self) -> dict[str, datetime]:
        if not database_is_configured():
            return dict(self._player_last_active)

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT player_id::text, COALESCE(last_offline_progress_at, updated_at, created_at)
                    FROM players
                    """
                )
                rows = cur.fetchall()
        return {str(row[0]): row[1].astimezone(UTC) for row in rows}

    def _load_ledger_entries(self) -> list[dict[str, Any]]:
        if not database_is_configured():
            return list(self._ledger_entries)

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT player_id, amount, currency, entry_type, created_at,
                           item_id, quantity, total_cost
                    FROM economy_player_ledger_entries
                    ORDER BY created_at DESC
                    LIMIT 5000
                    """
                )
                rows = cur.fetchall()
        return [
            {
                "player_id": row[0],
                "amount": row[1],
                "currency": row[2],
                "entry_type": row[3],
                "created_at": row[4].astimezone(UTC),
                "item_id": row[5],
                "quantity": row[6],
                "total_cost": row[7],
            }
            for row in rows
        ]

    @staticmethod
    def _pearson(xs: list[float], ys: list[float]) -> float:
        if not xs or not ys or len(xs) != len(ys):
            return 0.0
        n = len(xs)
        sum_x = sum(xs)
        sum_y = sum(ys)
        sum_x2 = sum(x * x for x in xs)
        sum_y2 = sum(y * y for y in ys)
        sum_xy = sum(x * y for x, y in zip(xs, ys, strict=False))
        numerator = (n * sum_xy) - (sum_x * sum_y)
        denom_left = (n * sum_x2) - (sum_x * sum_x)
        denom_right = (n * sum_y2) - (sum_y * sum_y)
        if denom_left <= 0 or denom_right <= 0:
            return 0.0
        denominator = (denom_left * denom_right) ** 0.5
        if denominator == 0:
            return 0.0
        return round(numerator / denominator, 6)
