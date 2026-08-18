extends Control
class_name GameplayShellPanel

@export var block_number_label_path: NodePath
@export var required_work_label_path: NodePath
@export var accumulated_work_label_path: NodePath
@export var progress_ratio_label_path: NodePath
@export var snapshot_cursor_label_path: NodePath
@export var rewards_total_label_path: NodePath
@export var ui_state_label_path: NodePath
@export var machine_name_label_path: NodePath
@export var machine_tier_label_path: NodePath
@export var base_hashrate_label_path: NodePath
@export var effective_hashrate_label_path: NodePath
@export var power_label_path: NodePath
@export var throttle_label_path: NodePath
@export var heat_label_path: NodePath
@export var cooling_label_path: NodePath
@export var base_hashrate_input_path: NodePath
@export var market_items_label_path: NodePath
@export var market_item_input_path: NodePath
@export var market_quantity_input_path: NodePath
@export var purchase_button_path: NodePath
@export var market_status_label_path: NodePath

var _view_model := GameplayShellViewModel.new()

func render_from_controller(controller: GameplayShellController) -> void:
	var status_ui := _view_model.map_status(controller.latest_status_payload)
	var snapshot_ui := _view_model.map_snapshot(controller.latest_snapshot_payload)
	var rewards_ui := _view_model.map_rewards(controller.latest_rewards_payload)
	var profile_ui := _view_model.map_profile(controller.latest_profile_payload)
	var market_ui := _view_model.map_market(controller.latest_status_payload)

	_set_label_text(block_number_label_path, "Block: %s" % status_ui.get("active_block_number_text", "-"))
	_set_label_text(required_work_label_path, "Required Work: %s" % status_ui.get("required_work_text", "0"))
	_set_label_text(accumulated_work_label_path, "Accumulated Work: %s" % status_ui.get("accumulated_work_text", "0"))
	_set_label_text(progress_ratio_label_path, "Progress: %s" % status_ui.get("progress_ratio_text", "0"))
	_set_label_text(snapshot_cursor_label_path, "Cursor: %s" % snapshot_ui.get("reconnect_cursor_text", "0"))
	_set_label_text(rewards_total_label_path, "Total Rewards: %s" % rewards_ui.get("total_rewards_text", "0"))
	_set_label_text(machine_name_label_path, "Machine: %s" % profile_ui.get("machine_name_text", "-"))
	_set_label_text(machine_tier_label_path, "Tier: %s" % profile_ui.get("tier_text", "-"))
	_set_label_text(base_hashrate_label_path, "Base Hashrate: %s" % profile_ui.get("base_hashrate_text", "0"))
	_set_label_text(effective_hashrate_label_path, "Effective Hashrate: %s" % profile_ui.get("effective_hashrate_text", "0"))
	_set_label_text(power_label_path, "Power: %s" % profile_ui.get("power_text", "0 / 0"))
	_set_label_text(throttle_label_path, "Power Throttle: %s" % profile_ui.get("power_throttle_text", "0"))
	_set_label_text(heat_label_path, "Heat: %s" % profile_ui.get("heat_text", "0"))
	_set_label_text(cooling_label_path, "Cooling: %s" % profile_ui.get("cooling_text", "0 / 0"))
	_set_line_edit_text(base_hashrate_input_path, str(profile_ui.get("base_hashrate_text", "0")))
	_set_label_text(market_items_label_path, "Market: %s" % market_ui.get("items_text", "No catalog loaded"))
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

func _set_line_edit_text(path: NodePath, value: String) -> void:
	if path.is_empty():
		return
	var input_node := get_node_or_null(path)
	if input_node is LineEdit:
		(input_node as LineEdit).text = value
		(input_node as LineEdit).editable = false
