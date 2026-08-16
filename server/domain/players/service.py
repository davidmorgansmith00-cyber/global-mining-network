from __future__ import annotations

from uuid import UUID

from domain.players.repository import PlayerRepository
from domain.players.schemas import BootstrapResponse, StarterMachine
from shared.database import database_is_configured


class PlayerBootstrapService:
    def __init__(self) -> None:
        self.repository = PlayerRepository()

    def bootstrap(self, player_id: str | None = None) -> BootstrapResponse:
        if database_is_configured() and player_id is not None:
            profile = self.repository.get_profile(UUID(player_id))
            if profile is not None:
                hardware_id, name, hashrate_hps = profile
                return BootstrapResponse(
                    player_id=player_id,
                    starter_machine=StarterMachine(
                        hardware_id=hardware_id,
                        name=name,
                        hashrate_hps=hashrate_hps,
                    ),
                )

        return BootstrapResponse(
            player_id=player_id or "player_placeholder",
            starter_machine=StarterMachine(
                hardware_id="starter_rusty_home_computer",
                name="Rusty Home Computer",
                hashrate_hps=12,
            ),
        )