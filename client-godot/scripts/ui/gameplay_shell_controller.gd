extends Node
class_name GameplayShellController

@export var api_base_url: String = "http://127.0.0.1:8000"
@export var websocket_base_url: String = "ws://127.0.0.1:8000"
@export var status_recent_limit: int = 10
@export var rewards_recent_limit: int = 20
@export var stream_limit: int = 100

var api_client: GmnApiClient
var stream_client: GmnStreamClient

var session_id: String = ""
var player_id: String = ""
var latest_status_payload: Dictionary = {}
var latest_snapshot_payload: Dictionary = {}
var latest_rewards_payload: Dictionary = {}
var latest_profile_payload: Dictionary = {}
var latest_blocks_payload: Dictionary = {}
var latest_history_payload: Dictionary = {}
var latest_events_payload: Dictionary = {}
var latest_pools_payload: Dictionary = {}
var latest_leaderboard_payload: Dictionary = {}
var latest_position_payload: Dictionary = {}
var ui_state := GameplayShellUiState.new()
var _refresh_in_progress := false

func _ready() -> void:
	api_client = GmnApiClient.new()
	api_client.configure(api_base_url)
	add_child(api_client)
	stream_client = GmnStreamClient.new()
	stream_client.configure(websocket_base_url)
	add_child(stream_client)

	# Server remains authoritative; this controller only transports and renders server-owned state.

func configure_session(player: String, session: String, access_token: String, refresh_token: String) -> void:
	player_id = player
	session_id = session
	api_client.set_session({
		"player_id": player,
		"session_id": session,
		"access_token": access_token,
		"refresh_token": refresh_token,
	})

func build_status_request_url() -> String:
	return api_client.build_status_url(status_recent_limit)

func build_snapshot_request_url() -> String:
	return api_client.build_snapshot_url(status_recent_limit)

func build_rewards_request_url() -> String:
	return api_client.build_rewards_url(player_id, rewards_recent_limit)

func build_profile_request_url() -> String:
	return api_client.build_player_profile_url(player_id)

func build_events_stream_url() -> String:
	return stream_client.build_global_events_url(player_id, session_id)

func acknowledge_stream_cursor(next_cursor: int) -> void:
	stream_client.acknowledge_cursor(next_cursor)

func register_and_store_session(email: String, password: String) -> Dictionary:
	var response: Dictionary = await api_client.register_session(email, password)
	if response.get("ok", false):
		var payload: Dictionary = response.get("payload", {})
		api_client.set_session(payload)
		player_id = str(payload.get("player_id", ""))
	return response

func login_and_store_session(email: String, password: String) -> Dictionary:
	var response: Dictionary = await api_client.login_session(email, password)
	if response.get("ok", false):
		var payload: Dictionary = response.get("payload", {})
		api_client.set_session(payload)
		player_id = str(payload.get("player_id", ""))
	return response

func refresh_authoritative_views() -> Dictionary:
	if _refresh_in_progress:
		return {"ok": false, "skipped": true, "error": "refresh_in_progress"}
	_refresh_in_progress = true
	if player_id == "":
		ui_state.set_unauthorized()
		_refresh_in_progress = false
		return {
			"status": {"ok": false, "error": "missing_player_id", "status_code": 401},
			"snapshot": {"ok": false, "error": "missing_player_id", "status_code": 401},
			"rewards": {"ok": false, "error": "missing_player_id", "status_code": 401},
			"profile": {"ok": false, "error": "missing_player_id", "status_code": 401},
			"blocks": {"ok": false, "error": "missing_player_id", "status_code": 401},
			"history": {"ok": false, "error": "missing_player_id", "status_code": 401},
			"events": {"ok": false, "error": "missing_player_id", "status_code": 401},
		}
	ui_state.set_loading()
	var status_response: Dictionary = await api_client.fetch_status(status_recent_limit)
	var snapshot_response: Dictionary = await api_client.fetch_snapshot(status_recent_limit)
	var rewards_response: Dictionary = await api_client.fetch_rewards(player_id, rewards_recent_limit)
	var profile_response: Dictionary = await api_client.fetch_player_profile(player_id)
	var blocks_response: Dictionary = await api_client.fetch_explorer_blocks()
	var history_response: Dictionary = await api_client.fetch_player_history(player_id)
	var events_response: Dictionary = await api_client.fetch_active_events()
	var pools_response: Dictionary = await api_client.fetch_pools()
	var leaderboard_response: Dictionary = await api_client.fetch_hashrate_leaderboard()
	var position_response: Dictionary = await api_client.fetch_player_leaderboard_position(player_id)
	var successful_response_count := 0

	if status_response.get("ok", false):
		successful_response_count += 1
		latest_status_payload = status_response.get("payload", {})
	if snapshot_response.get("ok", false):
		successful_response_count += 1
		latest_snapshot_payload = snapshot_response.get("payload", {})
		var snapshot_cursor := int(latest_snapshot_payload.get("reconnect_cursor", 0))
		stream_client.set_cursor(max(stream_client.reconnect_cursor, snapshot_cursor))
	if rewards_response.get("ok", false):
		successful_response_count += 1
		latest_rewards_payload = rewards_response.get("payload", {})
	if profile_response.get("ok", false):
		successful_response_count += 1
		latest_profile_payload = profile_response.get("payload", {})
	if blocks_response.get("ok", false):
		latest_blocks_payload = blocks_response.get("payload", {})
	if history_response.get("ok", false):
		latest_history_payload = history_response.get("payload", {})
	if events_response.get("ok", false):
		latest_events_payload = events_response.get("payload", {})
	if pools_response.get("ok", false):
		latest_pools_payload = pools_response.get("payload", {})
	if leaderboard_response.get("ok", false):
		latest_leaderboard_payload = leaderboard_response.get("payload", {})
	if position_response.get("ok", false):
		latest_position_payload = position_response.get("payload", {})

	if successful_response_count == 4:
		ui_state.set_ready()
	elif successful_response_count > 0:
		ui_state.set_stale("Some authoritative views could not be refreshed")
	else:
		var status_code := int(status_response.get("status_code", 0))
		if status_code == 401 or status_code == 403:
			ui_state.set_unauthorized()
		elif status_code == 503:
			ui_state.set_maintenance()
		else:
			ui_state.set_error()

	_refresh_in_progress = false
	return {
		"status": status_response,
		"snapshot": snapshot_response,
		"rewards": rewards_response,
		"profile": profile_response,
		"blocks": blocks_response,
		"history": history_response,
		"events": events_response,
		"pools": pools_response,
		"leaderboard": leaderboard_response,
		"position": position_response,
	}

func get_ui_state() -> Dictionary:
	return ui_state.to_display()

func get_server_base_hashrate() -> float:
	return float(latest_profile_payload.get("base_hashrate", 0.0))

func send_market_purchase(item_id: String, quantity: int) -> Dictionary:
	if session_id == "":
		return {"ok": false, "error": "missing_session_id"}
	return await api_client.send_market_purchase(item_id, quantity)

func restore_stream_cursor_from_checkpoint() -> Dictionary:
	if player_id == "" or session_id == "":
		return {
			"ok": false,
			"error": "missing_session_binding",
		}

	var response: Dictionary = await api_client.fetch_checkpoint("global", player_id, session_id)
	if response.get("ok", false):
		var payload: Dictionary = response.get("payload", {})
		stream_client.set_cursor(int(payload.get("reconnect_cursor", 0)))
	return response

func persist_stream_cursor_checkpoint() -> Dictionary:
	if player_id == "" or session_id == "":
		return {
			"ok": false,
			"error": "missing_session_binding",
		}

	return await api_client.upsert_checkpoint(
		"global",
		player_id,
		session_id,
		stream_client.reconnect_cursor,
	)

func connect_global_event_stream() -> int:
	if player_id == "" or session_id == "":
		return ERR_INVALID_PARAMETER
	return stream_client.connect_global_events(player_id, session_id, stream_limit)

func poll_stream_once() -> Array[Dictionary]:
	var raw_messages := stream_client.poll_stream_messages()
	var domain_messages: Array[Dictionary] = []

	for message in raw_messages:
		if str(message.get("type", "")) == "ping":
			stream_client.send_pong()
			continue

		if message.has("reconnect_cursor"):
			var cursor := int(message.get("reconnect_cursor", 0))
			if cursor > 0:
				stream_client.acknowledge_cursor(cursor)
				stream_client.send_cursor_ack(cursor)

		domain_messages.append(message)

	return domain_messages

func send_start_operation_intent(operation_id: String, base_hashrate_hps: float) -> Dictionary:
	# Intents are forwarded to the server; no local authoritative progression state is mutated.
	if player_id == "":
		return {
			"ok": false,
			"error": "missing_player_id",
		}
	return await api_client.send_operation_start_intent(operation_id, base_hashrate_hps)

func send_stop_operation_intent(operation_id: String) -> Dictionary:
	if player_id == "":
		return {
			"ok": false,
			"error": "missing_player_id",
		}
	return await api_client.send_operation_stop_intent(operation_id)
