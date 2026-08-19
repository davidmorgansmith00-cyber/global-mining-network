## GMN Pause Menu
## Clean, minimal. Options: Resume, Settings, Main Menu (confirm), Quit (confirm).
extends Control
class_name GmnPauseMenu

signal resume_requested
signal settings_requested
signal main_menu_requested
signal quit_requested

var _resume_button: GmnButton
var _settings_button: GmnButton
var _main_menu_button: GmnButton
var _quit_button: GmnButton

func _ready() -> void:
	var layout := VBoxContainer.new()
	layout.anchor_left = 0.5
	layout.anchor_top = 0.5
	layout.anchor_right = 0.5
	layout.anchor_bottom = 0.5
	layout.offset_left = -170.0
	layout.offset_top = -110.0
	layout.offset_right = 170.0
	layout.offset_bottom = 110.0
	layout.add_theme_constant_override("separation", 12)
	add_child(layout)
	_resume_button = _menu_button("RESUME", "primary")
	_settings_button = _menu_button("SETTINGS", "secondary")
	_main_menu_button = _menu_button("MAIN MENU", "secondary")
	_quit_button = _menu_button("QUIT", "danger")
	layout.add_child(_resume_button)
	layout.add_child(_settings_button)
	layout.add_child(_main_menu_button)
	layout.add_child(_quit_button)
	_resume_button.pressed.connect(func() -> void: resume_requested.emit())
	_settings_button.pressed.connect(func() -> void: settings_requested.emit())
	_main_menu_button.pressed.connect(func() -> void: main_menu_requested.emit())
	_quit_button.pressed.connect(func() -> void: quit_requested.emit())
	_link_focus_ring([_resume_button, _settings_button, _main_menu_button, _quit_button])
	_resume_button.grab_focus()

func _menu_button(label_text: String, variant_key: String) -> GmnButton:
	var button := GmnButton.new()
	button.text = label_text
	button.variant = variant_key
	button.focus_mode = Control.FOCUS_ALL
	return button

func _link_focus_ring(nodes: Array[Control]) -> void:
	for i in range(nodes.size()):
		var current := nodes[i]
		var previous := nodes[(i - 1 + nodes.size()) % nodes.size()]
		var next := nodes[(i + 1) % nodes.size()]
		current.focus_neighbor_top = current.get_path_to(previous)
		current.focus_neighbor_bottom = current.get_path_to(next)
