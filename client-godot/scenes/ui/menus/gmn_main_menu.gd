## GMN Main Menu
## GMN network identity; not an isolated save-game feel.
## Options: New Game, Continue, Settings, Credits, Quit.
extends Control
class_name GmnMainMenu

signal new_game_requested
signal continue_requested
signal settings_requested
signal credits_requested
signal quit_requested

const MENU_ITEMS := [
	{"id": "continue", "label": "CONTINUE"},
	{"id": "new_game", "label": "NEW GAME"},
	{"id": "settings", "label": "SETTINGS"},
	{"id": "credits", "label": "CREDITS"},
	{"id": "quit", "label": "QUIT"},
]

var _buttons: Dictionary = {}

func _ready() -> void:
	var list := VBoxContainer.new()
	list.anchor_left = 0.5
	list.anchor_top = 0.5
	list.anchor_right = 0.5
	list.anchor_bottom = 0.5
	list.offset_left = -160.0
	list.offset_top = -140.0
	list.offset_right = 160.0
	list.offset_bottom = 140.0
	list.add_theme_constant_override("separation", 12)
	add_child(list)
	for item in MENU_ITEMS:
		var button := GmnButton.new()
		button.variant = "primary" if item["id"] == "new_game" else "secondary"
		button.text = item["label"]
		button.focus_mode = Control.FOCUS_ALL
		button.pressed.connect(func() -> void: _emit_action(item["id"]))
		list.add_child(button)
		_buttons[item["id"]] = button
	_configure_focus_ring()
	var first_button: Control = _buttons.get("continue", _buttons.get("new_game"))
	if first_button:
		first_button.grab_focus()

func _emit_action(action_id: String) -> void:
	match action_id:
		"continue":
			continue_requested.emit()
		"new_game":
			new_game_requested.emit()
		"settings":
			settings_requested.emit()
		"credits":
			credits_requested.emit()
		"quit":
			quit_requested.emit()

func _configure_focus_ring() -> void:
	var ordered: Array[Control] = []
	for item in MENU_ITEMS:
		var button: Control = _buttons.get(item["id"])
		if button:
			ordered.append(button)
	for i in range(ordered.size()):
		var current: Control = ordered[i]
		var previous: Control = ordered[(i - 1 + ordered.size()) % ordered.size()]
		var next: Control = ordered[(i + 1) % ordered.size()]
		current.focus_neighbor_top = current.get_path_to(previous)
		current.focus_neighbor_bottom = current.get_path_to(next)
