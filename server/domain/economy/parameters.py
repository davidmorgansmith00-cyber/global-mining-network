from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
import json
from threading import Lock
from typing import Any

from shared.database import database_is_configured, open_connection


@dataclass(frozen=True)
class EconomyParameters:
    version: int
    difficulty_base: Decimal
    reward_per_work_unit: Decimal
    tier_unlock_times: dict[str, int]
    cosmetic_prices: dict[str, Decimal]
    battle_pass_price: Decimal
    event_frequency: str
    created_at: datetime
    reason: str
    admin_id: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "difficulty_base": str(self.difficulty_base),
            "reward_per_work_unit": str(self.reward_per_work_unit),
            "tier_unlock_times": self.tier_unlock_times,
            "cosmetic_prices": {k: str(v) for k, v in self.cosmetic_prices.items()},
            "battle_pass_price": str(self.battle_pass_price),
            "event_frequency": self.event_frequency,
            "created_at": self.created_at.astimezone(UTC).isoformat(),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class EconomyParameterHistoryEntry:
    parameter_version: int
    previous_version: int | None
    change_log: dict[str, Any]
    reverted_at: datetime | None = None
    reverted_by_admin_id: str | None = None


class EconomyParameterService:
    def __init__(self) -> None:
        self._lock = Lock()
        now = datetime.now(UTC)
        self._current = EconomyParameters(
            version=1,
            difficulty_base=Decimal("1.000000"),
            reward_per_work_unit=Decimal("0.100000"),
            tier_unlock_times={"tier_2": 3600, "tier_3": 21600, "tier_4": 86400},
            cosmetic_prices={"starter_skin": Decimal("100.000000")},
            battle_pass_price=Decimal("1000.000000"),
            event_frequency="daily",
            created_at=now,
            reason="initial_parameters",
            admin_id="system",
        )
        self._history: list[EconomyParameterHistoryEntry] = []
        self._versions: dict[int, EconomyParameters] = {1: self._current}

    def get_current_parameters(self) -> EconomyParameters:
        if database_is_configured():
            loaded = self._load_current_from_db()
            if loaded is not None:
                return loaded
        return self._current

    def get_history(self) -> list[EconomyParameterHistoryEntry]:
        if database_is_configured():
            loaded = self._load_history_from_db()
            if loaded:
                return loaded
        return list(self._history)

    def set_parameters(
        self,
        *,
        difficulty_base: Decimal,
        reward_per_work_unit: Decimal,
        tier_unlock_times: dict[str, int],
        cosmetic_prices: dict[str, Decimal],
        battle_pass_price: Decimal,
        event_frequency: str,
        reason: str,
        admin_id: str,
    ) -> EconomyParameters:
        with self._lock:
            previous = self.get_current_parameters()
            now = datetime.now(UTC)
            updated = EconomyParameters(
                version=previous.version + 1,
                difficulty_base=difficulty_base,
                reward_per_work_unit=reward_per_work_unit,
                tier_unlock_times=dict(tier_unlock_times),
                cosmetic_prices=dict(cosmetic_prices),
                battle_pass_price=battle_pass_price,
                event_frequency=event_frequency,
                created_at=now,
                reason=reason,
                admin_id=admin_id,
            )
            change_log = {
                "difficulty_base": [str(previous.difficulty_base), str(updated.difficulty_base)],
                "reward_per_work_unit": [str(previous.reward_per_work_unit), str(updated.reward_per_work_unit)],
                "tier_unlock_times": [previous.tier_unlock_times, updated.tier_unlock_times],
                "cosmetic_prices": [
                    {k: str(v) for k, v in previous.cosmetic_prices.items()},
                    {k: str(v) for k, v in updated.cosmetic_prices.items()},
                ],
                "battle_pass_price": [str(previous.battle_pass_price), str(updated.battle_pass_price)],
                "event_frequency": [previous.event_frequency, updated.event_frequency],
                "reason": reason,
            }
            history_entry = EconomyParameterHistoryEntry(
                parameter_version=updated.version,
                previous_version=previous.version,
                change_log=change_log,
            )
            if database_is_configured():
                self._insert_parameter_to_db(updated)
                self._insert_history_to_db(history_entry)
            self._current = updated
            self._history.append(history_entry)
            self._versions[updated.version] = updated
            return updated

    def rollback_to_version(self, *, target_version: int, admin_id: str, reason: str) -> EconomyParameters:
        target = self._get_version(target_version)
        if target is None:
            raise ValueError("target_version_not_found")

        updated = self.set_parameters(
            difficulty_base=target.difficulty_base,
            reward_per_work_unit=target.reward_per_work_unit,
            tier_unlock_times=target.tier_unlock_times,
            cosmetic_prices=target.cosmetic_prices,
            battle_pass_price=target.battle_pass_price,
            event_frequency=target.event_frequency,
            reason=reason,
            admin_id=admin_id,
        )

        if self._history:
            latest = self._history[-1]
            self._history[-1] = EconomyParameterHistoryEntry(
                parameter_version=latest.parameter_version,
                previous_version=latest.previous_version,
                change_log=latest.change_log,
                reverted_at=datetime.now(UTC),
                reverted_by_admin_id=admin_id,
            )
            if database_is_configured():
                self._mark_history_reverted(updated.version, admin_id)

        return updated

    def _get_version(self, version: int) -> EconomyParameters | None:
        return self._versions.get(version)

    @staticmethod
    def _from_row(row: tuple[Any, ...]) -> EconomyParameters:
        (
            version,
            difficulty_base,
            reward_per_work_unit,
            tier_unlock_times_json,
            cosmetic_prices_json,
            battle_pass_price,
            event_frequency,
            created_at,
            reason,
            admin_id,
        ) = row
        tier_unlock_times = json.loads(tier_unlock_times_json) if isinstance(tier_unlock_times_json, str) else tier_unlock_times_json
        cosmetic_raw = json.loads(cosmetic_prices_json) if isinstance(cosmetic_prices_json, str) else cosmetic_prices_json
        cosmetic_prices = {k: Decimal(str(v)) for k, v in cosmetic_raw.items()}
        return EconomyParameters(
            version=int(version),
            difficulty_base=Decimal(str(difficulty_base)),
            reward_per_work_unit=Decimal(str(reward_per_work_unit)),
            tier_unlock_times={k: int(v) for k, v in tier_unlock_times.items()},
            cosmetic_prices=cosmetic_prices,
            battle_pass_price=Decimal(str(battle_pass_price)),
            event_frequency=str(event_frequency),
            created_at=created_at.astimezone(UTC),
            reason=str(reason),
            admin_id=str(admin_id),
        )

    def _load_current_from_db(self) -> EconomyParameters | None:
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT version, difficulty_base, reward_per_work_unit,
                           tier_unlock_times_json::text, cosmetic_prices_json::text,
                           battle_pass_price, event_frequency, created_at, reason, admin_id
                    FROM economy_parameters
                    ORDER BY version DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
        if row is None:
            return None
        return self._from_row(row)

    def _load_history_from_db(self) -> list[EconomyParameterHistoryEntry]:
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT parameter_version, previous_version, change_log::text, reverted_at, reverted_by_admin_id
                    FROM economy_parameter_history
                    ORDER BY parameter_version DESC
                    """
                )
                rows = cur.fetchall()
        return [
            EconomyParameterHistoryEntry(
                parameter_version=int(row[0]),
                previous_version=int(row[1]) if row[1] is not None else None,
                change_log=json.loads(row[2]) if isinstance(row[2], str) else row[2],
                reverted_at=row[3],
                reverted_by_admin_id=row[4],
            )
            for row in rows
        ]

    def _insert_parameter_to_db(self, params: EconomyParameters) -> None:
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO economy_parameters (
                        version, difficulty_base, reward_per_work_unit, tier_unlock_times_json,
                        cosmetic_prices_json, battle_pass_price, event_frequency, created_at, reason, admin_id
                    )
                    VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s)
                    """,
                    (
                        params.version,
                        params.difficulty_base,
                        params.reward_per_work_unit,
                        json.dumps(params.tier_unlock_times),
                        json.dumps({k: str(v) for k, v in params.cosmetic_prices.items()}),
                        params.battle_pass_price,
                        params.event_frequency,
                        params.created_at,
                        params.reason,
                        params.admin_id,
                    ),
                )
            conn.commit()

    def _insert_history_to_db(self, history: EconomyParameterHistoryEntry) -> None:
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO economy_parameter_history (
                        parameter_version, previous_version, change_log, reverted_at, reverted_by_admin_id
                    )
                    VALUES (%s, %s, %s::jsonb, %s, %s)
                    """,
                    (
                        history.parameter_version,
                        history.previous_version,
                        json.dumps(history.change_log),
                        history.reverted_at,
                        history.reverted_by_admin_id,
                    ),
                )
            conn.commit()

    def _mark_history_reverted(self, parameter_version: int, admin_id: str) -> None:
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE economy_parameter_history
                    SET reverted_at = NOW(), reverted_by_admin_id = %s
                    WHERE parameter_version = %s
                    """,
                    (admin_id, parameter_version),
                )
            conn.commit()


_parameter_service: EconomyParameterService | None = None
_parameter_lock = Lock()


def get_economy_parameter_service() -> EconomyParameterService:
    global _parameter_service
    if _parameter_service is None:
        with _parameter_lock:
            if _parameter_service is None:
                _parameter_service = EconomyParameterService()
    return _parameter_service
