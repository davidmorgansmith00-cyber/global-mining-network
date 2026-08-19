## GMN Confirm Dialog
## Generic confirmation modal used by Pause Menu and destructive actions.
extends Control
class_name GmnConfirmDialog

signal confirmed
signal cancelled

@export var message: String = "Are you sure?":
	set(v): message = v; _refresh_message()

var _message_label: Label

func _ready() -> void:
	_message_label = Label.new()
	add_child(_message_label)
	_refresh_message()

func _refresh_message() -> void:
	if _message_label:
		_message_label.text = message
