## GMN Gameplay Shell Controller
## Orchestrates session bootstrap, status polling, and HUD updates
## Server-authoritative only - no client progression mutation

class_name GmnGameplayShellController
extends Node

## Services
var api_client: GmnApiClient
var session: GmnSession
var status_polling: GmnStatusPollingService
var status_hud: GmnBlockStatusHud

## Configuration
var status_polling_interval: float = 2.0

func _ready() -> void:
	# Initialize API client (handles session internally)
	api_client = GmnApiClient.new()
	add_child(api_client)
	
	# Get session reference
	session = api_client.get_session()
	
	# Create status polling service
	status_polling = GmnStatusPollingService.new()
	add_child(status_polling)
	status_polling.api_client = api_client
	
	# Create status HUD
	status_hud = GmnBlockStatusHud.new()
	add_child(status_hud)
	
	# Wire signals
	status_polling.status_updated.connect(_on_status_updated)
	status_polling.status_error.connect(_on_status_error)

## Bootstrap session and start gameplay
func bootstrap_session(email: String, password: String) -> Dictionary:
	# Register/login
	var login_response = await api_client.login_session(email, password)
	
	if not login_response.get("ok", false):
		return {
			"ok": false,
			"error": "Login failed: %s" % login_response.get("payload", {}).get("error", "Unknown error")
		}
	
	# Verify session is active
	if not api_client.is_authenticated():
		return {
			"ok": false,
			"error": "Session authentication failed"
		}
	
	# Start status polling
	status_polling.start_polling(status_polling_interval)
	
	return {
		"ok": true,
		"player_id": session.player_id,
		"message": "Session bootstrapped and polling started"
	}

## Handle status updates
func _on_status_updated(status_response: Dictionary) -> void:
	# Update HUD from server response
	status_hud.update_from_status(status_response)
	
	# Emit signal for other systems
	print("Status updated: Block %d, Progress %.1f%%" % [
		status_hud.get_current_block_number(),
		status_hud.get_current_progress_percent()
	])

## Handle status errors
func _on_status_error(error: String) -> void:
	print("Status error: %s" % error)

## Stop all services
func stop_services() -> void:
	status_polling.stop_polling()

## Set status polling interval
func set_status_polling_interval(interval: float) -> void:
	status_polling_interval = interval
	status_polling.set_polling_interval(interval)

## Get current status HUD
func get_status_hud() -> GmnBlockStatusHud:
	return status_hud

## Get current session
func get_session() -> GmnSession:
	return session

## Check if authenticated
func is_authenticated() -> bool:
	return api_client.is_authenticated()
