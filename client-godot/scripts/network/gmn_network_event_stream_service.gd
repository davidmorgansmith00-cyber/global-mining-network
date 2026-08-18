## GMN Network Event Stream Service
## Manages websocket connection and event deduplication

class_name GmnNetworkEventStreamService
extends Node

## Event stream state
var is_connected: bool = false
var reconnect_attempts: int = 0
var max_reconnect_attempts: int = 5
var reconnect_delay: float = 2.0

## Event processing
var processed_sequences: Dictionary = {}  # Track processed sequence IDs to avoid duplicates
var event_queue: Array = []

## Cursor management
var current_cursor: int = 0

## Signals
signal event_received(event: Dictionary)
signal connected
signal disconnected
signal reconnect_attempt(attempt: int)
signal stream_error(error: String)

## API client reference
var api_client: GmnApiClient = null
var websocket: WebSocketPeer = null
var reconnect_timer: Timer = null

func _ready() -> void:
	api_client = get_parent().get_node("GmnApiClient") if get_parent() != null else null
	
	# Create reconnect timer
	reconnect_timer = Timer.new()
	add_child(reconnect_timer)
	reconnect_timer.timeout.connect(_on_reconnect_timer_timeout)

## Connect to event stream with cursor
func connect_to_stream(cursor: int = 0) -> Dictionary:
	current_cursor = cursor
	
	if websocket != null:
		websocket.close()
	
	websocket = WebSocketPeer.new()
	
	# Construct websocket URL with cursor parameter
	var ws_url = "ws://localhost:8080/api/v1/blockchain/network-events/ws?after_sequence=%d" % cursor
	
	if not api_client:
		return {"ok": false, "error": "API client not available"}
	
	# Add auth header via session
	var error = websocket.connect_to_url(ws_url)
	if error != OK:
		stream_error.emit("Failed to connect to websocket: %s" % error)
		return {"ok": false, "error": "Websocket connection failed"}
	
	return {"ok": true, "message": "Connecting to event stream..."}

## Process incoming websocket messages
func _process(_delta: float) -> void:
	if websocket == null:
		return
	
	websocket.poll()
	
	var state = websocket.get_ready_state()
	
	if state == WebSocketPeer.STATE_OPEN:
		if not is_connected:
			is_connected = true
			reconnect_attempts = 0
			connected.emit()
		
		# Process all available messages
		while websocket.get_available_packet_count():
			var packet = websocket.get_message()
			if packet != null:
				_process_event(packet)
	
	elif state == WebSocketPeer.STATE_CLOSED:
		if is_connected:
			is_connected = false
			disconnected.emit()
			_attempt_reconnect()

## Process individual event from stream
func _process_event(event_bytes: PackedByteArray) -> void:
	var event_text = event_bytes.get_string_from_utf8()
	var event = JSON.parse_string(event_text)
	
	if event == null:
		stream_error.emit("Failed to parse event JSON")
		return
	
	# Extract sequence ID for deduplication
	var sequence = int(event.get("sequence", -1))
	
	if sequence == -1:
		stream_error.emit("Event missing sequence ID")
		return
	
	# Avoid duplicate event processing
	if processed_sequences.has(sequence):
		return  # Already processed
	
	processed_sequences[sequence] = true
	current_cursor = sequence
	
	# Emit event for consumption
	event_received.emit(event)

## Attempt to reconnect
func _attempt_reconnect() -> void:
	if reconnect_attempts >= max_reconnect_attempts:
		stream_error.emit("Max reconnection attempts reached")
		return
	
	reconnect_attempts += 1
	reconnect_attempt.emit(reconnect_attempts)
	
	# Wait and retry
	reconnect_timer.wait_time = reconnect_delay
	reconnect_timer.start()

## Reconnect timer timeout
func _on_reconnect_timer_timeout() -> void:
	reconnect_timer.stop()
	connect_to_stream(current_cursor)

## Disconnect from stream
func disconnect_from_stream() -> void:
	if websocket != null:
		websocket.close()
		websocket = null
	
	if reconnect_timer != null:
		reconnect_timer.stop()
	
	is_connected = false

## Get current cursor position
func get_current_cursor() -> int:
	return current_cursor

## Check if stream is connected
func is_stream_connected() -> bool:
	return is_connected

## Clear processed sequences (for testing)
func clear_processed_sequences() -> void:
	processed_sequences.clear()

## Get count of processed sequences
func get_processed_count() -> int:
	return processed_sequences.size()
