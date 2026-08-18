extends RefCounted
class_name GmnClientTelemetry

const ALLOWED_EVENTS := {
	"launcher_handoff_completed": true,
	"login_succeeded": true,
	"login_failed": true,
	"first_machine_viewed": true,
	"operation_intent_succeeded": true,
	"operation_intent_failed": true,
	"reconnect_succeeded": true,
	"reconnect_failed": true,
	"accessibility_setting_changed": true,
}
const PRIVATE_KEYS := ["email", "password", "access_token", "refresh_token", "session_id", "player_id"]

var _events: Array[Dictionary] = []

func record(event_name: String, properties: Dictionary = {}) -> void:
	if not ALLOWED_EVENTS.has(event_name):
		return
	_events.append({
		"event_name": event_name,
		"properties": _sanitize_properties(properties),
		"client_version": "0.1.0",
		"recorded_at_unix_seconds": int(Time.get_unix_time_from_system()),
	})

func drain() -> Array[Dictionary]:
	var result := _events.duplicate(true)
	_events.clear()
	return result

func size() -> int:
	return _events.size()

func _sanitize_properties(properties: Dictionary) -> Dictionary:
	var safe: Dictionary = {}
	for key_variant in properties.keys():
		var key := str(key_variant)
		if key in PRIVATE_KEYS:
			continue
		safe[key] = properties[key_variant]
	return safe
