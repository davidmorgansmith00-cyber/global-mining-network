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
