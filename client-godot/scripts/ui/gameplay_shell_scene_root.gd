extends Control
class_name GameplayShellSceneRoot

@export var controller_node_path: NodePath = NodePath("GameplayShellController")
@export var panel_node_path: NodePath = NodePath("GameplayShellPanel")
@export var operation_id_input_path: NodePath = NodePath("GameplayShellPanel/OperationIdInput")
@export var base_hashrate_input_path: NodePath = NodePath("GameplayShellPanel/BaseHashrateInput")
@export var start_operation_button_path: NodePath = NodePath("GameplayShellPanel/StartOperationButton")
@export var stop_operation_button_path: NodePath = NodePath("GameplayShellPanel/StopOperationButton")
@export var action_status_label_path: NodePath = NodePath("GameplayShellPanel/ActionStatusLabel")
@export var ui_state_label_path: NodePath = NodePath("GameplayShellPanel/UiStateLabel")
@export var refresh_interval_seconds: float = 3.0
@export var auto_render: bool = true

var _controller: GameplayShellController
var _panel: GameplayShellPanel
var _operation_id_input: LineEdit
var _base_hashrate_input: LineEdit
var _start_operation_button: Button
var _stop_operation_button: Button
var _action_status_label: Label
var _time_until_refresh: float = 0.0

func _ready() -> void:
	_controller = get_node_or_null(controller_node_path)
	_panel = get_node_or_null(panel_node_path)
	_operation_id_input = get_node_or_null(operation_id_input_path)
	_base_hashrate_input = get_node_or_null(base_hashrate_input_path)
	_start_operation_button = get_node_or_null(start_operation_button_path)
	_stop_operation_button = get_node_or_null(stop_operation_button_path)
	_action_status_label = get_node_or_null(action_status_label_path)
	if _controller == null or _panel == null:
		push_warning("Gameplay shell scene is missing controller or panel binding")
		return

	_bind_action_signals()

	_time_until_refresh = refresh_interval_seconds
	if auto_render:
		_panel.render_from_controller(_controller)

func _process(delta: float) -> void:
	if _controller == null or _panel == null:
		return

	for _message in _controller.poll_stream_once():
		pass

	_time_until_refresh -= delta
	if _time_until_refresh <= 0.0:
		_time_until_refresh = refresh_interval_seconds
		var _ignored = await _controller.refresh_authoritative_views()
		if auto_render:
			_panel.render_from_controller(_controller)

func refresh_now() -> void:
	if _controller == null or _panel == null:
		return
	var _ignored = await _controller.refresh_authoritative_views()
	_panel.render_from_controller(_controller)

func _bind_action_signals() -> void:
	if _start_operation_button != null and not _start_operation_button.pressed.is_connected(_on_start_operation_pressed):
		_start_operation_button.pressed.connect(_on_start_operation_pressed)
	if _stop_operation_button != null and not _stop_operation_button.pressed.is_connected(_on_stop_operation_pressed):
		_stop_operation_button.pressed.connect(_on_stop_operation_pressed)

func _on_start_operation_pressed() -> void:
	if _controller == null:
		return
	var operation_id := _operation_id_input.text.strip_edges() if _operation_id_input != null else ""
	if operation_id == "":
		_set_action_status("Start rejected: operation_id is required")
		return

	var hashrate_text := _base_hashrate_input.text.strip_edges() if _base_hashrate_input != null else ""
	var parsed_hashrate := hashrate_text.to_float()
	if parsed_hashrate <= 0:
		_set_action_status("Start rejected: base hashrate must be > 0")
		return

	_set_action_status("Sending start intent...")
	var response: Dictionary = await _controller.send_start_operation_intent(operation_id, parsed_hashrate)
	_set_action_status(_format_action_response("start", response))

func _on_stop_operation_pressed() -> void:
	if _controller == null:
		return
	var operation_id := _operation_id_input.text.strip_edges() if _operation_id_input != null else ""
	if operation_id == "":
		_set_action_status("Stop rejected: operation_id is required")
		return

	_set_action_status("Sending stop intent...")
	var response: Dictionary = await _controller.send_stop_operation_intent(operation_id)
	_set_action_status(_format_action_response("stop", response))

func _set_action_status(text: String) -> void:
	if _action_status_label != null:
		_action_status_label.text = text

func _format_action_response(action: String, response: Dictionary) -> String:
	if not response.get("ok", false):
		var status_code := int(response.get("status_code", 0))
		return "%s intent failed (status=%d)" % [action, status_code]

	var payload: Variant = response.get("payload", {})
	if payload is Dictionary:
		var detail := str((payload as Dictionary).get("detail", "accepted"))
		var status_value := str((payload as Dictionary).get("status", "ok"))
		return "%s intent %s: %s" % [action, status_value, detail]
	return "%s intent accepted" % action
