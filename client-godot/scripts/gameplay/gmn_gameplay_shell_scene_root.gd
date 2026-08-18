## GMN Gameplay Shell Scene Root
## Main scene for gameplay UI and service orchestration

class_name GmnGameplayShellSceneRoot
extends Control

## UI References
@onready var block_number_label: Label = Label.new()
@onready var accumulated_work_label: Label = Label.new()
@onready var required_work_label: Label = Label.new()
@onready var progress_bar: ProgressBar = ProgressBar.new()
@onready var status_text: Label = Label.new()

@onready var operation_id_input: LineEdit = LineEdit.new()
@onready var hashrate_input: LineEdit = LineEdit.new()
@onready var start_button: Button = Button.new()
@onready var stop_button: Button = Button.new()
@onready var operation_status_label: Label = Label.new()

@onready var reward_list: ItemList = ItemList.new()

@onready var error_panel: PanelContainer = PanelContainer.new()
@onready var error_label: Label = Label.new()

## Services
var controller: GmnGameplayShellController = null

func _ready() -> void:
	# Create main container
	var main_container = VBoxContainer.new()
	add_child(main_container)
	
	# Title
	var title = Label.new()
	title.text = "Global Mining Network - Gameplay"
	main_container.add_child(title)
	
	# Status Panel
	_create_status_panel(main_container)
	
	# Operations Panel
	_create_operations_panel(main_container)
	
	# Reward Panel
	_create_reward_panel(main_container)
	
	# Error Panel
	_create_error_panel(main_container)
	
	# Initialize controller
	controller = GmnGameplayShellController.new()
	add_child(controller)
	
	# Wire signals
	controller.status_polling.status_updated.connect(_on_status_updated)
	controller.status_polling.status_error.connect(_on_status_error)
	start_button.pressed.connect(_on_start_operation)
	stop_button.pressed.connect(_on_stop_operation)

## Create status display panel
func _create_status_panel(parent: Control) -> void:
	var panel = PanelContainer.new()
	parent.add_child(panel)
	
	var vbox = VBoxContainer.new()
	panel.add_child(vbox)
	
	block_number_label.text = "Block: 0"
	vbox.add_child(block_number_label)
	
	accumulated_work_label.text = "Accumulated Work: 0.0 hps"
	vbox.add_child(accumulated_work_label)
	
	required_work_label.text = "Required Work: 0.0 hps"
	vbox.add_child(required_work_label)
	
	progress_bar.min_value = 0
	progress_bar.max_value = 100
	progress_bar.value = 0
	vbox.add_child(progress_bar)
	
	status_text.text = "Status: Connecting..."
	vbox.add_child(status_text)

## Create operations control panel
func _create_operations_panel(parent: Control) -> void:
	var panel = PanelContainer.new()
	parent.add_child(panel)
	
	var vbox = VBoxContainer.new()
	panel.add_child(vbox)
	
	var title = Label.new()
	title.text = "Operations"
	vbox.add_child(title)
	
	operation_id_input.placeholder_text = "Operation ID"
	vbox.add_child(operation_id_input)
	
	hashrate_input.placeholder_text = "Base Hashrate (hps)"
	vbox.add_child(hashrate_input)
	
	var hbox = HBoxContainer.new()
	vbox.add_child(hbox)
	
	start_button.text = "Start Operation"
	hbox.add_child(start_button)
	
	stop_button.text = "Stop Operation"
	hbox.add_child(stop_button)
	
	operation_status_label.text = "Operation Status: Idle"
	vbox.add_child(operation_status_label)

## Create reward display panel
func _create_reward_panel(parent: Control) -> void:
	var panel = PanelContainer.new()
	parent.add_child(panel)
	
	var vbox = VBoxContainer.new()
	panel.add_child(vbox)
	
	var title = Label.new()
	title.text = "Rewards"
	vbox.add_child(title)
	
	reward_list.custom_minimum_size = Vector2(0, 200)
	vbox.add_child(reward_list)

## Create error panel
func _create_error_panel(parent: Control) -> void:
	error_panel.visible = false
	parent.add_child(error_panel)
	
	error_label.text = "Error: Connection lost"
	error_panel.add_child(error_label)

## Handle status updates
func _on_status_updated(status_response: Dictionary) -> void:
	var hud = controller.get_status_hud()
	
	block_number_label.text = "Block: %d" % hud.get_current_block_number()
	accumulated_work_label.text = "Accumulated Work: %.2f hps" % hud.get_current_accumulated_work()
	required_work_label.text = "Required Work: %.2f hps" % hud.get_current_required_work()
	progress_bar.value = int(hud.get_current_progress_percent())
	status_text.text = "Status: Block %d (%.1f%%)" % [hud.get_current_block_number(), hud.get_current_progress_percent()]
	
	# Hide error panel on success
	error_panel.visible = false

## Handle status errors
func _on_status_error(error: String) -> void:
	error_label.text = "Error: %s" % error
	error_panel.visible = true

## Handle start operation button
func _on_start_operation() -> void:
	var operation_id = operation_id_input.text
	var hashrate_str = hashrate_input.text
	
	if operation_id == "" or hashrate_str == "":
		error_label.text = "Error: Operation ID and Hashrate required"
		error_panel.visible = true
		return
	
	var hashrate = float(hashrate_str)
	
	# Send start intent to server
	var response = await controller.api_client.send_operation_start_intent(operation_id, hashrate)
	
	if response.get("ok", false):
		operation_status_label.text = "Operation Status: Running (%s)" % operation_id
		error_panel.visible = false
	else:
		error_label.text = "Error: Failed to start operation"
		error_panel.visible = true

## Handle stop operation button
func _on_stop_operation() -> void:
	var operation_id = operation_id_input.text
	
	if operation_id == "":
		error_label.text = "Error: Operation ID required"
		error_panel.visible = true
		return
	
	# Send stop intent to server
	var response = await controller.api_client.send_operation_stop_intent(operation_id)
	
	if response.get("ok", false):
		operation_status_label.text = "Operation Status: Stopped"
		operation_id_input.text = ""
		hashrate_input.text = ""
		error_panel.visible = false
	else:
		error_label.text = "Error: Failed to stop operation"
		error_panel.visible = true

## Bootstrap gameplay session
func bootstrap_session(email: String, password: String) -> Dictionary:
	return await controller.bootstrap_session(email, password)

## Get controller reference
func get_controller() -> GmnGameplayShellController:
	return controller
