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
        yield "block_number,block_id,difficulty,reward_pool,miners_count,completion_time\n"
        offset = 0
        while True:
            rows = self._explorer_service.get_blocks(
                limit=500,
                offset=offset,
                start_date=start_date,
                end_date=end_date,
            )
            if not rows:
                break
            for row in rows:
                yield (
                    f"{row['block_number']},{row['block_id']},{row['difficulty']},{row['reward_pool']},"
                    f"{row['miners_count']},{row['completion_time']}\n"
                )
            if len(rows) < 500:
                break
            offset += 500

    def export_transactions_json(
        self,
        player_id: str | None,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> Generator[str, None, None]:
        yield "["
        offset = 0
        wrote_any = False
        while True:
            rows = self._explorer_service.get_transactions(
                transaction_type=None,
                player_id=player_id,
                limit=500,
                offset=offset,
                start_date=start_date,
                end_date=end_date,
            )
            if not rows:
                break
            for row in rows:
                if wrote_any:
                    yield ","
                yield json.dumps(row, separators=(",", ":"))
                wrote_any = True
            if len(rows) < 500:
                break
            offset += 500
        yield "]"

    def export_pool_history_csv(self, pool_id: str) -> Generator[str, None, None]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["pool_id", "event_type", "player_id", "amount", "timestamp"])
        yield buffer.getvalue()
        buffer.truncate(0)
        buffer.seek(0)
        offset = 0
        while True:
            rows = self._explorer_service.get_pool_history(
                pool_id=pool_id,
                limit=500,
                offset=offset,
                start_date=None,
                end_date=None,
            )
            if not rows:
                break
            for row in rows:
                writer.writerow([row["pool_id"], row["event_type"], row["player_id"], row["amount"], row["timestamp"]])
            yield buffer.getvalue()
            buffer.truncate(0)
            buffer.seek(0)
            if len(rows) < 500:
                break
            offset += 500
