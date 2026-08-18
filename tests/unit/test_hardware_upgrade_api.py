from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"
for path in (str(ROOT), str(SERVER_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.main import app


client = TestClient(app)


def test_start_upgrade_rejects_invalid_session() -> None:
    response = client.post(
        "/api/v1/hardware/upgrades/start?session_id=not-a-uuid",
        json={"hardware_id": "improved_workstation", "idempotency_key": "upgrade-test-1"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_session"


def test_current_upgrade_rejects_player_session_mismatch() -> None:
    response = client.get(
        "/api/v1/hardware/upgrades/current"
        "?player_id=00000000-0000-0000-0000-000000000000"
        "&session_id=not-a-uuid"
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid_session"
