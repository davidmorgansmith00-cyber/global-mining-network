## GMN Player Reward Timeline Service
## Fetches and manages player reward history from server

class_name GmnPlayerRewardTimelineService
extends Node

## Reward data
var reward_entries: Array = []  # Array of server reward entries
var is_loaded: bool = false
var player_id: String = ""
var last_fetch_timestamp: int = 0

## Signals
signal rewards_loaded(entries: Array)
signal rewards_updated(entries: Array)
signal empty_state_reached
signal fetch_error(error: String)

## API client reference
var api_client: GmnApiClient = null

func _ready() -> void:
	api_client = get_parent().get_node("GmnApiClient") if has_parent() else null

## Set active player (called after successful login)
func set_player_id(id: String) -> void:
	player_id = id

## Fetch rewards from server
func fetch_rewards() -> Dictionary:
	if player_id == "":
		return {"ok": false, "error": "Player ID not set"}
	
	if not api_client:
		return {"ok": false, "error": "API client not available"}
	
	# Fetch from server endpoint: GET /api/v1/blockchain/players/{player_id}/rewards
	var response = await api_client.fetch_player_rewards(player_id)
	
	if not response.get("ok", false):
		var error = response.get("error", "Failed to fetch rewards")
		fetch_error.emit(error)
		return response
	
	# Extract reward entries from payload
	var entries = response.get("payload", {}).get("rewards", [])
	
	# Validate: entries must be server-provided, read-only
	# No client-side calculation or mutation allowed
	reward_entries = entries
	is_loaded = true
	last_fetch_timestamp = Time.get_ticks_msec()
	
	# Signal empty state if no rewards
	if reward_entries.is_empty():
		empty_state_reached.emit()
	else:
		rewards_loaded.emit(reward_entries)
	
	return response

## Get reward entries
func get_reward_entries() -> Array:
	return reward_entries.duplicate()

## Check if rewards are loaded
func is_rewards_loaded() -> bool:
	return is_loaded

## Get entry count
func get_entry_count() -> int:
	return reward_entries.size()

## Check if empty
func is_empty() -> bool:
	return reward_entries.is_empty()

## Get specific reward entry by index
func get_reward_entry(index: int) -> Dictionary:
	if index < 0 or index >= reward_entries.size():
		return {}
	return reward_entries[index]

## Validate entry structure (no client mutation)
func _validate_entry_structure(entry: Dictionary) -> bool:
	# Entry must have: block_number, reward_amount, contribution_hash
	# These are server-provided and read-only
	return entry.has("block_number") and \
	       entry.has("reward_amount") and \
	       entry.has("contribution_hash")

## Clear rewards (on logout)
func clear_rewards() -> void:
	reward_entries.clear()
	is_loaded = false
	player_id = ""
	last_fetch_timestamp = 0

## Format entry for display (no calculations, only field mapping)
func format_entry_for_display(entry: Dictionary) -> Dictionary:
	return {
		"block": entry.get("block_number", 0),
		"amount": entry.get("reward_amount", 0.0),
		"hash": entry.get("contribution_hash", "")
	}
