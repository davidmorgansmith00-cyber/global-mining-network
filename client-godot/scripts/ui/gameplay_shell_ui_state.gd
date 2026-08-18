extends RefCounted
class_name GameplayShellUiState

const LOADING := "loading"
const READY := "ready"
const STALE := "stale"
const ERROR := "error"
const UNAUTHORIZED := "unauthorized"
const MAINTENANCE := "maintenance"

var state_code: String = LOADING
var message: String = "Connecting to the network..."
var last_updated_unix_seconds: int = 0

func set_loading() -> void:
	_set_state(LOADING, "Refreshing authoritative network state...")

func set_ready() -> void:
	_set_state(READY, "Live authoritative state")

func set_stale(detail: String = "Some authoritative data is stale") -> void:
	_set_state(STALE, detail)

func set_error(detail: String = "Unable to load authoritative state") -> void:
	_set_state(ERROR, detail)

func set_unauthorized() -> void:
	_set_state(UNAUTHORIZED, "Session expired. Sign in again to continue.")

func set_maintenance(detail: String = "The network is in maintenance mode") -> void:
	_set_state(MAINTENANCE, detail)

func to_display() -> Dictionary:
	return {
		"state_code": state_code,
		"message": message,
		"last_updated_unix_seconds": last_updated_unix_seconds,
	}

func _set_state(next_state: String, next_message: String) -> void:
	state_code = next_state
	message = next_message
	if next_state == READY:
		last_updated_unix_seconds = int(Time.get_unix_time_from_system())
