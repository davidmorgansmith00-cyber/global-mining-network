from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP

from domain.blockchain.network_stream import NetworkEventStream, get_network_event_stream
from domain.blockchain.schemas import (
    BlockchainStatusResponse,
    NetworkEventEnvelope,
    NetworkEventsResponse,
    NetworkFinalizationSnapshot,
    NetworkSnapshotContract,
    PlayerRewardHistoryItem,
    PlayerRewardHistoryResponse,
    RecentBlockOutcome,
)
from domain.market.service import NpcMarketService
from shared.database import database_is_configured, open_connection


RATIO_QUANTIZE = Decimal("0.000001")


class BlockchainReadModelService:
    def __init__(self, network_event_stream: NetworkEventStream | None = None) -> None:
        self.network_event_stream = network_event_stream or get_network_event_stream()
        self.market_service = NpcMarketService()

    def get_status(self, *, recent_limit: int = 10) -> BlockchainStatusResponse:
        market_catalog = self.market_service.get_market_catalog()
        if not database_is_configured():
            return BlockchainStatusResponse(
                active_block_number=1,
                active_required_work=Decimal("100"),
                active_accumulated_work=Decimal("0"),
                active_progress_ratio=Decimal("0"),
                recent_outcomes=[],
                market_catalog=market_catalog,
            )

        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT block_number, required_work, accumulated_work
                    FROM blockchain_active_block
                    WHERE singleton_id = TRUE
                    """
                )
                active_row = cursor.fetchone()
                if active_row is None:
                    active_block_number = 1
                    active_required_work = Decimal("100")
                    active_accumulated_work = Decimal("0")
                else:
                    active_block_number = active_row[0]
                    active_required_work = active_row[1]
                    active_accumulated_work = active_row[2]

                cursor.execute(
                    """
                    SELECT
                        fb.block_number,
                        fb.required_work,
                        fb.total_work,
                        fb.finalized_at,
                        COALESCE(pool.reward_pool_amount, 0) AS reward_pool_amount,
                        COALESCE(players.player_reward_amount, 0) AS player_reward_amount
                    FROM blockchain_finalized_blocks fb
                    LEFT JOIN (
                        SELECT reference_block_number AS block_number, SUM(amount) AS reward_pool_amount
                        FROM economy_ledger_entries
                        WHERE entry_type = 'block.finalized.reward_pool.v1'
                        GROUP BY reference_block_number
                    ) pool ON pool.block_number = fb.block_number
                    LEFT JOIN (
                        SELECT block_number, SUM(amount) AS player_reward_amount
                        FROM economy_player_ledger_entries
                        WHERE entry_type = 'block.finalized.player_reward.v1'
                        GROUP BY block_number
                    ) players ON players.block_number = fb.block_number
                    ORDER BY fb.block_number DESC
                    LIMIT %s
                    """,
                    (recent_limit,),
                )
                rows = cursor.fetchall()

        progress_ratio = Decimal("0")
        if active_required_work > 0:
            progress_ratio = (active_accumulated_work / active_required_work).quantize(
                RATIO_QUANTIZE,
                rounding=ROUND_HALF_UP,
            )

        outcomes = [
            RecentBlockOutcome(
                block_number=row[0],
                required_work=row[1],
                total_work=row[2],
                finalized_at=row[3],
                reward_pool_amount=row[4],
                player_reward_amount=row[5],
            )
            for row in rows
        ]

        return BlockchainStatusResponse(
            active_block_number=active_block_number,
            active_required_work=active_required_work,
            active_accumulated_work=active_accumulated_work,
            active_progress_ratio=progress_ratio,
            recent_outcomes=outcomes,
            market_catalog=market_catalog,
        )

    def get_player_reward_history(self, *, player_id: str, recent_limit: int = 20) -> PlayerRewardHistoryResponse:
        if not database_is_configured():
            return PlayerRewardHistoryResponse(
                player_id=player_id,
                total_rewards=Decimal("0"),
                total_contribution_hashes=Decimal("0"),
                entries=[],
            )

        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        pel.block_number,
                        pel.amount,
                        pel.contribution_hashes,
                        fb.finalized_at
                    FROM economy_player_ledger_entries pel
                    JOIN blockchain_finalized_blocks fb
                        ON fb.block_number = pel.block_number
                    WHERE pel.player_id = %s
                      AND pel.entry_type = 'block.finalized.player_reward.v1'
                    ORDER BY pel.block_number DESC
                    LIMIT %s
                    """,
                    (player_id, recent_limit),
                )
                rows = cursor.fetchall()

        entries = [
            PlayerRewardHistoryItem(
                block_number=row[0],
                reward_amount=row[1],
                contribution_hashes=row[2],
                finalized_at=row[3],
            )
            for row in rows
        ]

        return PlayerRewardHistoryResponse(
            player_id=player_id,
            total_rewards=sum((item.reward_amount for item in entries), Decimal("0")),
            total_contribution_hashes=sum((item.contribution_hashes for item in entries), Decimal("0")),
            entries=entries,
        )

    def get_network_snapshot_contract(self, *, recent_limit: int = 10) -> NetworkSnapshotContract:
        status = self.get_status(recent_limit=recent_limit)
        latest_sequence = self.network_event_stream.latest_sequence()
        recent = [
            NetworkFinalizationSnapshot(
                block_number=item.block_number,
                required_work=item.required_work,
                total_work=item.total_work,
                reward_pool_amount=item.reward_pool_amount,
                player_reward_amount=item.player_reward_amount,
                finalized_at=item.finalized_at,
            )
            for item in status.recent_outcomes
        ]
        return NetworkSnapshotContract(
            schema_version="network.snapshot.v1",
            generated_at=datetime.now(UTC),
            snapshot_sequence=latest_sequence,
            reconnect_cursor=latest_sequence,
            active_block_number=status.active_block_number,
            active_required_work=status.active_required_work,
            active_accumulated_work=status.active_accumulated_work,
            active_progress_ratio=status.active_progress_ratio,
            recent_finalizations=recent,
        )

    def get_network_events(self, *, after_sequence: int | None, limit: int = 100) -> NetworkEventsResponse:
        events = self.network_event_stream.list_after(after_sequence=after_sequence, limit=limit)
        latest = self.network_event_stream.latest_sequence()
        envelopes = [
            NetworkEventEnvelope(
                sequence=item.sequence,
                event_type=item.event_type,
                occurred_at=item.occurred_at,
                payload=item.payload,
            )
            for item in events
        ]
        return NetworkEventsResponse(
            schema_version="network.events.v1",
            reconnect_cursor=latest,
            latest_sequence=latest,
            events=envelopes,
        )

    def get_network_events_for_channel(
        self,
        *,
        channel: str,
        player_id: str,
        after_sequence: int | None,
        limit: int = 100,
    ) -> NetworkEventsResponse:
        stream_events = self.network_event_stream.list_after(after_sequence=after_sequence, limit=limit * 4)
        if channel == "global":
            filtered = [
                item
                for item in stream_events
                if item.event_type in {"network.block_progress.v1", "network.block_finalized.v1"}
            ]
        elif channel == "player_rewards":
            filtered = [
                item
                for item in stream_events
                if item.event_type == "network.player_reward.v1" and str(item.payload.get("player_id")) == player_id
            ]
        else:
            filtered = []

        trimmed = filtered[:limit]
        latest = self.network_event_stream.latest_sequence()
        envelopes = [
            NetworkEventEnvelope(
                sequence=item.sequence,
                event_type=item.event_type,
                occurred_at=item.occurred_at,
                payload=item.payload,
            )
            for item in trimmed
        ]
        reconnect_cursor = latest if not envelopes else envelopes[-1].sequence
        return NetworkEventsResponse(
            schema_version="network.events.v1",
            reconnect_cursor=reconnect_cursor,
            latest_sequence=latest,
            events=envelopes,
        )
