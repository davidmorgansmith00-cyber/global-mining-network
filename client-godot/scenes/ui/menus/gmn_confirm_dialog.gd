## GMN Confirm Dialog
## Generic confirmation modal used by Pause Menu and destructive actions.
extends Control
class_name GmnConfirmDialog

signal confirmed
signal cancelled

@export var message: String = "Are you sure?":
	set(v): message = v; _refresh_message()

var _message_label: Label
var _confirm_button: GmnButton
var _cancel_button: GmnButton

func _ready() -> void:
	var layout := VBoxContainer.new()
	layout.add_theme_constant_override("separation", 10)
	add_child(layout)
	_message_label = Label.new()
	_message_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	layout.add_child(_message_label)
	var row := HBoxContainer.new()
	layout.add_child(row)
	_confirm_button = GmnButton.new()
	_confirm_button.variant = "danger"
	_confirm_button.text = "CONFIRM"
	_cancel_button = GmnButton.new()
	_cancel_button.variant = "secondary"
	_cancel_button.text = "CANCEL"
	row.add_child(_confirm_button)
	row.add_child(_cancel_button)
	_confirm_button.pressed.connect(func() -> void: confirmed.emit())
	_cancel_button.pressed.connect(func() -> void: cancelled.emit())
	_confirm_button.focus_neighbor_right = _confirm_button.get_path_to(_cancel_button)
	_cancel_button.focus_neighbor_left = _cancel_button.get_path_to(_confirm_button)
	_confirm_button.grab_focus()
	_refresh_message()

func _refresh_message() -> void:
	if _message_label:
		_message_label.text = message

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_accept"):
		confirmed.emit()
	elif event.is_action_pressed("ui_cancel"):
		cancelled.emit()
