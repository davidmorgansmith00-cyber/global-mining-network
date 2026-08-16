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
	var status_response: Dictionary = await api_client.fetch_status(status_recent_limit)
	var snapshot_response: Dictionary = await api_client.fetch_snapshot(status_recent_limit)
	var rewards_response: Dictionary = await api_client.fetch_rewards(player_id, rewards_recent_limit)

	if status_response.get("ok", false):
		latest_status_payload = status_response.get("payload", {})
	if snapshot_response.get("ok", false):
		latest_snapshot_payload = snapshot_response.get("payload", {})
		var snapshot_cursor := int(latest_snapshot_payload.get("reconnect_cursor", 0))
		stream_client.set_cursor(max(stream_client.reconnect_cursor, snapshot_cursor))
	if rewards_response.get("ok", false):
		latest_rewards_payload = rewards_response.get("payload", {})

	return {
		"status": status_response,
		"snapshot": snapshot_response,
		"rewards": rewards_response,
	}

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
