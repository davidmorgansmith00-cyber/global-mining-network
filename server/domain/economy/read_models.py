from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from shared.database import database_is_configured, open_connection


@dataclass(frozen=True)
class PlayerRewardBalance:
    player_id: str
    reward_balance: Decimal


def project_player_reward_balances() -> list[PlayerRewardBalance]:
    if not database_is_configured():
        return []

    with open_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT player_id, COALESCE(SUM(amount), 0) AS reward_balance
                FROM economy_player_ledger_entries
                GROUP BY player_id
                ORDER BY player_id ASC
                """
            )
            rows = cursor.fetchall()

    return [
        PlayerRewardBalance(
            player_id=row[0],
            reward_balance=row[1],
        )
        for row in rows
    ]