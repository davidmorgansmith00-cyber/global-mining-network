from __future__ import annotations

from datetime import UTC, datetime
import logging
import time

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = ROOT / "server"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.blockchain.network_stream import get_network_event_stream
from domain.events.service import EventService


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("gmn.event_processor")


def run_once(event_service: EventService | None = None) -> list[str]:
    service = event_service or EventService()
    resolved_event_ids = service.resolve_expired_fork_events()
    stream = get_network_event_stream()
    for event_id in resolved_event_ids:
        stream.publish(
            event_type="event_resolved",
            payload={"event_id": event_id, "resolved_at": datetime.now(UTC).isoformat()},
        )
    return resolved_event_ids


def main() -> None:
    logger.info("event_processor_started interval_seconds=60")
    while True:
        try:
            resolved = run_once()
            if resolved:
                logger.info("event_processor_resolved count=%s event_ids=%s", len(resolved), ",".join(resolved))
        except Exception as exc:  # pragma: no cover - defensive worker safety
            logger.exception("event_processor_failed error=%s", str(exc))
        time.sleep(60)


if __name__ == "__main__":
    main()
