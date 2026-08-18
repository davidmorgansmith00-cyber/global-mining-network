extends RefCounted
class_name GameplayShellViewModel

# Converts authoritative payloads into UI-ready fields without introducing client authority.
func map_status(payload: Dictionary) -> Dictionary:
	return {
		"active_block_number_text": str(payload.get("active_block_number", "-")),
		"required_work_text": str(payload.get("active_required_work", "0")),
		"accumulated_work_text": str(payload.get("active_accumulated_work", "0")),
		"progress_ratio_text": str(payload.get("active_progress_ratio", "0")),
		"recent_outcomes_count_text": str((payload.get("recent_outcomes", []) as Array).size()),
	}

func map_snapshot(payload: Dictionary) -> Dictionary:
	return {
		"snapshot_sequence_text": str(payload.get("snapshot_sequence", 0)),
		"reconnect_cursor_text": str(payload.get("reconnect_cursor", 0)),
		"recent_finalizations_count_text": str((payload.get("recent_finalizations", []) as Array).size()),
	}

func map_rewards(payload: Dictionary) -> Dictionary:
	return {
		"player_id_text": str(payload.get("player_id", "")),
		"total_rewards_text": str(payload.get("total_rewards", "0")),
		"total_contribution_hashes_text": str(payload.get("total_contribution_hashes", "0")),
		"reward_entries_count_text": str((payload.get("entries", []) as Array).size()),
	}

func map_profile(payload: Dictionary) -> Dictionary:
	var hardware := payload.get("current_hardware", {}) as Dictionary
	return {
		"machine_name_text": str(hardware.get("name", payload.get("hardware_id", "-"))),
		"base_hashrate_text": str(payload.get("base_hashrate", "0")),
		"effective_hashrate_text": str(payload.get("effective_hashrate", "0")),
		"power_text": "%s / %s" % [str(payload.get("power_consumed", "0")), str(payload.get("power_capacity", "0"))],
		"power_throttle_text": str(payload.get("power_throttle_multiplier", "0")),
		"heat_text": str(payload.get("heat_generated", "0")),
		"cooling_text": "%s / %s" % [str(payload.get("cooling_efficiency_multiplier", "0")), str(payload.get("cooling_capacity", "0"))],
		"tier_text": str(payload.get("player_tier", "0")),
	}

func map_market(payload: Dictionary) -> Dictionary:
	var items := payload.get("market_catalog", []) as Array
	var names: Array[String] = []
	for item_variant in items:
		var item := item_variant as Dictionary
		names.append("%s (%s)" % [str(item.get("item_id", "-")), str(item.get("price", "-"))])
	return {
		"items_text": "%d items available" % items.size(),
		"item_names_text": " | ".join(names),
		"item_count_text": str(items.size()),
	}

func map_history(blocks_payload: Dictionary, player_payload: Dictionary, events_payload: Dictionary) -> Dictionary:
	var blocks := blocks_payload.get("items", []) as Array
	var history := player_payload.get("items", []) as Array
	var events := events_payload.get("items", []) as Array
	return {
		"blocks_text": "Blocks: %d" % blocks.size(),
		"player_history_text": "Your records: %d" % history.size(),
		"events_text": "Active events: %d" % events.size(),
	}
