extends Control
class_name GameplayShellPanel

@export var block_number_label_path: NodePath
@export var required_work_label_path: NodePath
@export var accumulated_work_label_path: NodePath
@export var progress_ratio_label_path: NodePath
@export var snapshot_cursor_label_path: NodePath
@export var rewards_total_label_path: NodePath
@export var ui_state_label_path: NodePath

var _view_model := GameplayShellViewModel.new()

func render_from_controller(controller: GameplayShellController) -> void:
	var status_ui := _view_model.map_status(controller.latest_status_payload)
	var snapshot_ui := _view_model.map_snapshot(controller.latest_snapshot_payload)
	var rewards_ui := _view_model.map_rewards(controller.latest_rewards_payload)

	_set_label_text(block_number_label_path, "Block: %s" % status_ui.get("active_block_number_text", "-"))
	_set_label_text(required_work_label_path, "Required Work: %s" % status_ui.get("required_work_text", "0"))
	_set_label_text(accumulated_work_label_path, "Accumulated Work: %s" % status_ui.get("accumulated_work_text", "0"))
	_set_label_text(progress_ratio_label_path, "Progress: %s" % status_ui.get("progress_ratio_text", "0"))
	_set_label_text(snapshot_cursor_label_path, "Cursor: %s" % snapshot_ui.get("reconnect_cursor_text", "0"))
	_set_label_text(rewards_total_label_path, "Total Rewards: %s" % rewards_ui.get("total_rewards_text", "0"))
	var state_ui := controller.get_ui_state()
	_set_label_text(ui_state_label_path, "State: %s - %s" % [
		str(state_ui.get("state_code", "loading")),
		str(state_ui.get("message", "Connecting to the network...")),
	])

func _set_label_text(path: NodePath, value: String) -> void:
	if path.is_empty():
		return
	var label_node := get_node_or_null(path)
	if label_node == null:
		return
	if label_node.has_method("set_text"):
		label_node.call("set_text", value)
