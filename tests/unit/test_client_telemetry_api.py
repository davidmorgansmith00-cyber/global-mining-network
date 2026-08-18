from pathlib import Path
import queue
import sys
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"
for path in (str(ROOT), str(SERVER_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from domain.telemetry.service import PlayerTelemetryService


def test_client_event_allowlist_and_private_field_scrubbing() -> None:
    event_queue = queue.Queue()
    service = PlayerTelemetryService(buf=event_queue, backend=Mock())

    accepted = service.emit_client_event(
        event_type="login_succeeded",
        player_id="player-a",
        session_id="session-a",
        properties={"mode": "login", "player_id": "private", "access_token": "private"},
    )

    event = event_queue.get_nowait()
    assert accepted is True
    assert event.event_type == "client.login_succeeded"
    assert event.properties == {"mode": "login"}
    assert service.emit_client_event(
        event_type="unsupported_event",
        player_id="player-a",
        session_id="session-a",
        properties={},
    ) is False
