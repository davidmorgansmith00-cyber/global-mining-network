extends RefCounted
class_name GmnContractValidationSmoke

func run() -> Dictionary:
	var failures: Array[String] = []

	_validate_required_keys(
		{
			"active_block_number": 2,
			"active_required_work": "100.000000",
			"active_accumulated_work": "0.000000",
			"active_progress_ratio": "0.000000",
			"recent_outcomes": [],
		},
		GmnContracts.STATUS_KEYS.values(),
		"status",
		failures
	)

	_validate_required_keys(
		{
			"schema_version": "network.snapshot.v1",
			"snapshot_sequence": 5,
			"reconnect_cursor": 5,
			"active_block_number": 2,
			"active_required_work": "100.000000",
			"active_accumulated_work": "0.000000",
			"active_progress_ratio": "0.000000",
			"recent_finalizations": [],
		},
		GmnContracts.SNAPSHOT_KEYS.values(),
		"snapshot",
		failures
	)

	_validate_required_keys(
		{
			"schema_version": "network.events.v1",
			"reconnect_cursor": 5,
			"latest_sequence": 5,
			"events": [],
		},
		GmnContracts.EVENTS_KEYS.values(),
		"events",
		failures
	)

	_validate_required_keys(
		{
			"player_id": "player_a",
			"total_rewards": "100.000000",
			"total_contribution_hashes": "100.000000",
			"entries": [],
		},
		GmnContracts.REWARD_KEYS.values(),
		"rewards",
		failures
	)

	_validate_required_keys(
		{
			"player_id": "player_a",
			"session_id": "session_a",
			"channel": "global",
			"reconnect_cursor": 7,
		},
		GmnContracts.CHECKPOINT_KEYS.values(),
		"checkpoint",
		failures
	)

	return {
		"ok": failures.is_empty(),
		"failures": failures,
	}

func _validate_required_keys(payload: Dictionary, keys: Array, label: String, failures: Array[String]) -> void:
	for key_variant in keys:
		var key_name := str(key_variant)
		if not payload.has(key_name):
			failures.append("%s missing key: %s" % [label, key_name])
