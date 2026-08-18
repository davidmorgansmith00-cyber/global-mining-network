## GMN Network Snapshot Service
## Loads initial network state and manages event stream cursor

class_name GmnNetworkSnapshotService
extends Node

## Snapshot data
var snapshot_data: Dictionary = {}
var snapshot_loaded: bool = false
var last_event_sequence: int = 0

## Cursor persistence
var cursor_file_path: String = "user://gmn_event_cursor.json"

## Signals
signal snapshot_loaded_signal(snapshot: Dictionary)
signal cursor_updated(sequence: int)
signal snapshot_error(error: String)

## API client reference
var api_client: GmnApiClient = null

func _ready() -> void:
	api_client = get_parent().get_node("GmnApiClient") if get_parent() != null else null

## Load initial snapshot from server
func load_snapshot() -> Dictionary:
	if not api_client:
		return {"ok": false, "error": "API client not available"}
	
	var response = await api_client.fetch_snapshot()
	
	if not response.get("ok", false):
		snapshot_error.emit(response.get("error", "Unknown error"))
		return response
	
	snapshot_data = response.get("payload", {})
	snapshot_loaded = true
	
	# Extract starting sequence from snapshot
	last_event_sequence = int(snapshot_data.get("event_sequence_at_snapshot", 0))
	
	snapshot_loaded_signal.emit(snapshot_data)
	return response

## Load persisted cursor from disk
func load_cursor_from_disk() -> int:
	if not FileAccess.file_exists(cursor_file_path):
		return 0
	
	var file = FileAccess.open(cursor_file_path, FileAccess.READ)
	if file == null:
		return 0
	
	var cursor_data = JSON.parse_string(file.get_as_text())
	if cursor_data == null:
		return 0
	
	return int(cursor_data.get("last_sequence", 0))

## Save cursor to disk for reconnection
func save_cursor_to_disk(sequence: int) -> bool:
	var cursor_data = {
		"last_sequence": sequence,
		"saved_at": Time.get_ticks_msec()
	}
	
	var file = FileAccess.open(cursor_file_path, FileAccess.WRITE)
	if file == null:
		return false
	
	file.store_string(JSON.stringify(cursor_data))
	return true

## Update event sequence and persist cursor
func update_cursor(new_sequence: int) -> void:
	if new_sequence > last_event_sequence:
		last_event_sequence = new_sequence
		save_cursor_to_disk(new_sequence)
		cursor_updated.emit(new_sequence)

## Get snapshot data
func get_snapshot() -> Dictionary:
	return snapshot_data

## Check if snapshot is loaded
func is_snapshot_loaded() -> bool:
	return snapshot_loaded

## Get current cursor position
func get_current_cursor() -> int:
	return last_event_sequence

## Get reconnect cursor (loads from disk if available)
func get_reconnect_cursor() -> int:
	var persisted_cursor = load_cursor_from_disk()
	if persisted_cursor > 0:
		return persisted_cursor
	return last_event_sequence
