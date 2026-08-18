extends Node

var _payload: Dictionary = {}

func set_session(payload: Dictionary) -> void:
	_payload = {
		"player_id": str(payload.get("player_id", "")),
		"session_id": str(payload.get("session_id", "")),
		"access_token": str(payload.get("access_token", "")),
		"refresh_token": str(payload.get("refresh_token", "")),
	}

func has_session() -> bool:
	return str(_payload.get("player_id", "")) != "" and str(_payload.get("access_token", "")) != ""

func get_session() -> Dictionary:
	return _payload.duplicate()

func clear() -> void:
	_payload.clear()
