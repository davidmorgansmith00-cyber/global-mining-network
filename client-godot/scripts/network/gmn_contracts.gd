extends RefCounted
class_name GmnContracts

# Centralized contract keys for authoritative API payloads.
const STATUS_SCHEMA := "blockchain.status.v1"
const SNAPSHOT_SCHEMA := "network.snapshot.v1"
const EVENTS_SCHEMA := "network.events.v1"

const STATUS_KEYS := {
	"active_block_number": "active_block_number",
	"active_required_work": "active_required_work",
	"active_accumulated_work": "active_accumulated_work",
	"active_progress_ratio": "active_progress_ratio",
	"recent_outcomes": "recent_outcomes",
}

const SNAPSHOT_KEYS := {
	"schema_version": "schema_version",
	"snapshot_sequence": "snapshot_sequence",
	"reconnect_cursor": "reconnect_cursor",
	"active_block_number": "active_block_number",
	"active_required_work": "active_required_work",
	"active_accumulated_work": "active_accumulated_work",
	"active_progress_ratio": "active_progress_ratio",
	"recent_finalizations": "recent_finalizations",
}

const EVENTS_KEYS := {
	"schema_version": "schema_version",
	"reconnect_cursor": "reconnect_cursor",
	"latest_sequence": "latest_sequence",
	"events": "events",
}

const REWARD_KEYS := {
	"player_id": "player_id",
	"total_rewards": "total_rewards",
	"total_contribution_hashes": "total_contribution_hashes",
	"entries": "entries",
}

const CHECKPOINT_KEYS := {
	"player_id": "player_id",
	"session_id": "session_id",
	"channel": "channel",
	"reconnect_cursor": "reconnect_cursor",
}
