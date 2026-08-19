## GMN Tab Bar
## Shared tabs with enforced keyboard/controller focus graph.
extends HBoxContainer
class_name GmnTabBar

signal tab_selected(tab_id: String)

@export var tabs: PackedStringArray = ["VIDEO", "AUDIO", "INPUT", "GAMEPLAY"]:
	set(value):
		tabs = value
		if is_inside_tree():
			_build_tabs()

@export var active_tab: String = "VIDEO"

var _buttons: Dictionary = {}

func _ready() -> void:
	_build_tabs()

func select_tab(tab_id: String) -> void:
	var upper := tab_id.to_upper()
	if upper not in tabs:
		return
	active_tab = upper
	for tab in tabs:
		var button: Button = _buttons.get(tab)
		if button == null:
			continue
		if tab == active_tab:
			button.add_theme_color_override("font_color", GmnUiTokens.ACCENT_PRIMARY)
		else:
			button.remove_theme_color_override("font_color")
	tab_selected.emit(active_tab)

func _build_tabs() -> void:
	for child in get_children():
		child.queue_free()
	_buttons.clear()
	for tab in tabs:
		var button := Button.new()
		button.text = tab
		button.focus_mode = Control.FOCUS_ALL
		button.pressed.connect(func() -> void: select_tab(tab))
		add_child(button)
		_buttons[tab] = button
	_enforce_focus_ring()
	if active_tab == "" and tabs.size() > 0:
		active_tab = tabs[0]
	select_tab(active_tab)

func _enforce_focus_ring() -> void:
	for i in range(tabs.size()):
		var tab := tabs[i]
		var button: Button = _buttons.get(tab)
		if button == null:
			continue
		var left_tab := tabs[(i - 1 + tabs.size()) % tabs.size()]
		var right_tab := tabs[(i + 1) % tabs.size()]
		var left_button: Button = _buttons.get(left_tab)
		var right_button: Button = _buttons.get(right_tab)
		if left_button:
			button.focus_neighbor_left = button.get_path_to(left_button)
		if right_button:
			button.focus_neighbor_right = button.get_path_to(right_button)

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_page_up"):
		_step(-1)
	elif event.is_action_pressed("ui_page_down"):
		_step(1)

func _step(direction: int) -> void:
	if tabs.is_empty():
		return
	var index := tabs.find(active_tab)
	if index < 0:
		index = 0
	var next_index := (index + direction + tabs.size()) % tabs.size()
	select_tab(tabs[next_index])
