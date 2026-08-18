## GMN Status Polling Service
## Handles periodic fetching of authoritative blockchain status
## Configurable polling interval with fallback from websocket

class_name GmnStatusPollingService
extends Node

## Polling configuration
var polling_interval: float = 2.0  # Default 2 seconds
var is_polling: bool = false
var api_client: GmnApiClient = null

## Signals
signal status_updated(status: Dictionary)
signal status_error(error: String)

func _ready() -> void:
	api_client = get_parent().get_node("GmnApiClient") if has_parent() else null

## Start polling for status updates
func start_polling(interval: float = 2.0) -> void:
	if is_polling:
		return
	
	polling_interval = interval
	is_polling = true
	_polling_loop()

## Stop polling
func stop_polling() -> void:
	is_polling = false

## Fetch status once
func fetch_status_once() -> Dictionary:
	if not api_client:
		return {"ok": false, "error": "API client not available"}
	
	var response = await api_client.fetch_status()
	return response

## Internal polling loop
func _polling_loop() -> void:
	while is_polling:
		var response = await fetch_status_once()
		
		if response.get("ok", false):
			status_updated.emit(response)
		else:
			status_error.emit(response.get("error", "Unknown error"))
		
		# Wait for next interval
		await get_tree().create_timer(polling_interval).timeout

## Set polling interval
func set_polling_interval(interval: float) -> void:
	polling_interval = max(0.5, interval)  # Minimum 0.5 seconds

## Get current polling interval
func get_polling_interval() -> float:
	return polling_interval

## Check if currently polling
func is_active() -> bool:
	return is_polling
