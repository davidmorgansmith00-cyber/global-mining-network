## GMN Operation Intent Service
## Handles start/stop operation intents with session binding

class_name GmnOperationIntentService
extends Node

## Active session reference
var active_session_id: String = ""
var player_id: String = ""

## Operation state tracking
var active_operations: Dictionary = {}  # Track currently running operations
var last_operation_response: Dictionary = {}

## Signals
signal operation_started(operation_id: String, hashrate: float)
signal operation_stopped(operation_id: String)
signal intent_error(error: String)
signal session_binding_error(error: String)

## API client reference
var api_client: GmnApiClient = null

func _ready() -> void:
	api_client = get_parent().get_node("GmnApiClient") if get_parent() != null else null

## Set active session (called after successful login)
func set_active_session(session_id: String, player_id_value: String) -> void:
	active_session_id = session_id
	player_id = player_id_value

## Verify session is active
func is_session_active() -> bool:
	return active_session_id != "" and player_id != ""

## Get active session ID
func get_active_session_id() -> String:
	return active_session_id

## Send start operation intent
func send_start_intent(operation_id: String, base_hashrate_hps: float) -> Dictionary:
	# Validate session binding
	if not is_session_active():
		var error = "Session binding error: no active session"
		session_binding_error.emit(error)
		return {"ok": false, "error": error}
	
	# Build payload with ONLY operation_id and base_hashrate_hps
	# NO player_id in payload - server derives from session
	var payload = {
		"operation_id": operation_id,
		"base_hashrate_hps": base_hashrate_hps
	}
	
	# Send request with session_id as query parameter
	if not api_client:
		return {"ok": false, "error": "API client not available"}
	
	var response = await api_client.send_operation_start(operation_id, base_hashrate_hps, active_session_id)
	
	if not response.get("ok", false):
		var error = response.get("error", "Start intent failed")
		
		# Check if error is session-binding related
		if "session" in error.to_lower() or "unauthorized" in error.to_lower():
			session_binding_error.emit(error)
		else:
			intent_error.emit(error)
		
		last_operation_response = response
		return response
	
	# Track active operation
	active_operations[operation_id] = {
		"hashrate": base_hashrate_hps,
		"started_at": Time.get_ticks_msec()
	}
	
	last_operation_response = response
	operation_started.emit(operation_id, base_hashrate_hps)
	
	return response

## Send stop operation intent
func send_stop_intent(operation_id: String) -> Dictionary:
	# Validate session binding
	if not is_session_active():
		var error = "Session binding error: no active session"
		session_binding_error.emit(error)
		return {"ok": false, "error": error}
	
	# Build payload with ONLY operation_id
	# NO player_id in payload - server derives from session
	var payload = {
		"operation_id": operation_id
	}
	
	# Send request with session_id as query parameter
	if not api_client:
		return {"ok": false, "error": "API client not available"}
	
	var response = await api_client.send_operation_stop(operation_id, active_session_id)
	
	if not response.get("ok", false):
		var error = response.get("error", "Stop intent failed")
		
		# Check if error is session-binding related
		if "session" in error.to_lower() or "unauthorized" in error.to_lower():
			session_binding_error.emit(error)
		else:
			intent_error.emit(error)
		
		last_operation_response = response
		return response
	
	# Remove from active operations
	if active_operations.has(operation_id):
		active_operations.erase(operation_id)
	
	last_operation_response = response
	operation_stopped.emit(operation_id)
	
	return response

## Get active operations
func get_active_operations() -> Dictionary:
	return active_operations.duplicate()

## Check if operation is active
func is_operation_active(operation_id: String) -> bool:
	return active_operations.has(operation_id)

## Get last response
func get_last_response() -> Dictionary:
	return last_operation_response

## Clear session (called on logout)
func clear_session() -> void:
	active_session_id = ""
	player_id = ""
	active_operations.clear()
