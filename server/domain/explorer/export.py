from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from typing import Generator

from domain.explorer.service import ChainExplorerService


class ExportService:
    def __init__(self, *, explorer_service: ChainExplorerService | None = None) -> None:
        self._explorer_service = explorer_service or ChainExplorerService()

    def export_blocks_csv(self, start_date: datetime | None, end_date: datetime | None) -> Generator[str, None, None]:
        rows = self._explorer_service.get_blocks(limit=500, offset=0)
        start_at = start_date or datetime(1970, 1, 1, tzinfo=UTC)
        end_at = end_date or datetime.now(UTC)
        yield "block_number,block_id,difficulty,reward_pool,miners_count,completion_time\n"
        for row in rows:
            completion_time = datetime.fromisoformat(row["completion_time"])
            if completion_time < start_at or completion_time > end_at:
                continue
            yield (
                f"{row['block_number']},{row['block_id']},{row['difficulty']},{row['reward_pool']},"
                f"{row['miners_count']},{row['completion_time']}\n"
            )

    def export_transactions_json(
        self,
        player_id: str | None,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> Generator[str, None, None]:
        rows = self._explorer_service.get_transactions(
            type=None,
            player_id=player_id,
            limit=500,
            offset=0,
            start_date=start_date,
            end_date=end_date,
        )
        yield "["
        for index, row in enumerate(rows):
            if index > 0:
                yield ","
            yield json.dumps(row, separators=(",", ":"))
        yield "]"

    def export_pool_history_csv(self, pool_id: str) -> Generator[str, None, None]:
        rows = self._explorer_service.get_pool_history(pool_id=pool_id, limit=500, offset=0, start_date=None, end_date=None)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["pool_id", "event_type", "player_id", "amount", "timestamp"])
        for row in rows:
            writer.writerow([row["pool_id"], row["event_type"], row["player_id"], row["amount"], row["timestamp"]])
        yield buffer.getvalue()
