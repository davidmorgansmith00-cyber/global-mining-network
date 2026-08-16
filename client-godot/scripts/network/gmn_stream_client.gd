extends Node
class_name GmnStreamClient

const EVENTS_WS_PATH := "/api/v1/blockchain/network-events/ws"

var ws_base_url: String = "ws://127.0.0.1:8000"
var reconnect_cursor: int = 0
var _socket: WebSocketPeer

func configure(base_url: String) -> void:
	ws_base_url = base_url.rstrip("/")

func build_global_events_url(player_id: String, session_id: String, limit: int = 100) -> String:
	return "%s%s?after_sequence=%d&limit=%d&player_id=%s&session_id=%s&channel=global" % [
		ws_base_url,
		EVENTS_WS_PATH,
		reconnect_cursor,
		limit,
		player_id,
		session_id,
	]

func acknowledge_cursor(next_cursor: int) -> void:
	if next_cursor > reconnect_cursor:
		reconnect_cursor = next_cursor

func set_cursor(next_cursor: int) -> void:
	reconnect_cursor = max(0, next_cursor)

func connect_global_events(player_id: String, session_id: String, limit: int = 100) -> int:
	disconnect_stream()
	_socket = WebSocketPeer.new()
	return _socket.connect_to_url(build_global_events_url(player_id, session_id, limit))

func disconnect_stream() -> void:
	if _socket == null:
		return
	if _socket.get_ready_state() != WebSocketPeer.STATE_CLOSED:
		_socket.close()
	_socket = null

func is_stream_open() -> bool:
	if _socket == null:
		return false
	return _socket.get_ready_state() == WebSocketPeer.STATE_OPEN

func poll_stream_messages() -> Array[Dictionary]:
	if _socket == null:
		return []

	_socket.poll()
	if _socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		return []

	var messages: Array[Dictionary] = []
	while _socket.get_available_packet_count() > 0:
		var packet_text := _socket.get_packet().get_string_from_utf8()
		var parsed = JSON.parse_string(packet_text)
		if parsed is Dictionary:
			messages.append(parsed)

	return messages

func send_pong() -> int:
	if not is_stream_open():
		return ERR_UNAVAILABLE
	return _socket.send_text("pong")

func send_cursor_ack(cursor: int) -> int:
	if not is_stream_open():
		return ERR_UNAVAILABLE
	return _socket.send_text("cursor:%d" % cursor)
