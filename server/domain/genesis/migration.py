from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
import json
from threading import Lock
from uuid import uuid4

from shared.database import database_is_configured, open_connection


BALANCE_TRANSFER_RATIO = Decimal("0.90")
LOSS_TAX_RATIO = Decimal("0.10")


@dataclass(frozen=True)
class MigrationAuditEntry:
    beta_player_id: str
    production_player_id: str
    beta_balance: Decimal
    transferred_balance: Decimal
    loss_tax: Decimal
    migrated_at: datetime


class BetaMigrationService:
    def __init__(
        self,
        *,
        beta_profiles: dict[str, dict] | None = None,
        production_profiles: dict[str, dict] | None = None,
    ) -> None:
        self._beta_profiles = beta_profiles or {}
        self._production_profiles = production_profiles or {}
        self._migrated_pairs: set[tuple[str, str]] = set()
        self._audit_entries: list[MigrationAuditEntry] = []
        self._lock = Lock()

    def calculate_migration_loss_tax(self, beta_balance: Decimal) -> Decimal:
        return (beta_balance * LOSS_TAX_RATIO).quantize(Decimal("0.000001"))

    def verify_migration_data(self, beta_player_id: str, production_player_id: str) -> dict[str, object]:
        errors: list[str] = []
        if beta_player_id == production_player_id:
            errors.append("source_and_target_must_differ")
        if (beta_player_id, production_player_id) in self._migrated_pairs:
            errors.append("duplicate_migration_pair")
        beta_profile = self._beta_profiles.get(beta_player_id)
        if beta_profile is None:
            errors.append("beta_player_not_found")
        else:
            balance = Decimal(str(beta_profile.get("balance", "0")))
            if balance < 0:
                errors.append("negative_balance")
            if balance > Decimal("1000000000"):
                errors.append("balance_out_of_range")
        return {"valid": len(errors) == 0, "errors": errors}

    def migrate_beta_player(self, beta_player_id: str, production_player_id: str) -> dict[str, object]:
        with self._lock:
            verification = self.verify_migration_data(beta_player_id, production_player_id)
            if not verification["valid"]:
                return {"success": False, "errors": verification["errors"]}
            beta_profile = self._beta_profiles[beta_player_id]
            production_profile = self._production_profiles.setdefault(
                production_player_id,
                {
                    "balance": Decimal("0"),
                    "tier": 1,
                    "progress_to_next_tier": 0.0,
                    "inventory": [],
                    "blocks_mined": 0,
                    "total_rewards_earned": Decimal("0"),
                },
            )

            beta_balance = Decimal(str(beta_profile.get("balance", "0")))
            loss_tax = self.calculate_migration_loss_tax(beta_balance)
            transferred_balance = (beta_balance * BALANCE_TRANSFER_RATIO).quantize(Decimal("0.000001"))

            production_profile["balance"] = Decimal(str(production_profile.get("balance", "0"))) + transferred_balance
            production_profile["tier"] = int(beta_profile.get("tier", production_profile.get("tier", 1)))
            production_profile["progress_to_next_tier"] = float(beta_profile.get("progress_to_next_tier", 0.0))

            beta_inventory = beta_profile.get("inventory", [])
            transferable_inventory = [
                item for item in beta_inventory
                if str(item.get("category", "")).lower() not in {"currency", "credits"}
            ]
            existing = list(production_profile.get("inventory", []))
            production_profile["inventory"] = existing + transferable_inventory

            production_profile["blocks_mined"] = int(beta_profile.get("blocks_mined", 0))
            production_profile["total_rewards_earned"] = Decimal(str(beta_profile.get("total_rewards_earned", "0")))

            self._migrated_pairs.add((beta_player_id, production_player_id))
            audit_entry = MigrationAuditEntry(
                beta_player_id=beta_player_id,
                production_player_id=production_player_id,
                beta_balance=beta_balance,
                transferred_balance=transferred_balance,
                loss_tax=loss_tax,
                migrated_at=datetime.now(UTC),
            )
            self._audit_entries.append(audit_entry)

            self._record_ledger_migration(audit_entry)

            return {
                "success": True,
                "beta_player_id": beta_player_id,
                "production_player_id": production_player_id,
                "beta_balance": str(beta_balance),
                "transferred_balance": str(transferred_balance),
                "loss_tax": str(loss_tax),
                "ledger_entry_type": "beta_migration",
                "non_reversible": True,
            }

    def get_audit_entries(self) -> list[MigrationAuditEntry]:
        return list(self._audit_entries)

    def _record_ledger_migration(self, audit: MigrationAuditEntry) -> None:
        if not database_is_configured():
            return

        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO economy_player_ledger_entries (
                        ledger_entry_id,
                        block_number,
                        player_id,
                        amount,
                        contribution_hashes,
                        currency,
                        entry_type,
                        metadata,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        uuid4(),
                        None,
                        audit.production_player_id,
                        audit.transferred_balance,
                        Decimal("0"),
                        "credits",
                        "beta_migration",
                        json.dumps(
                            {
                                "beta_player_id": audit.beta_player_id,
                                "production_player_id": audit.production_player_id,
                                "beta_balance": str(audit.beta_balance),
                                "loss_tax": str(audit.loss_tax),
                            }
                        ),
                        audit.migrated_at,
                    ),
                )
            connection.commit()
