## GMN Nav Bar
## Primary navigation: MINE | HARDWARE | POWER | STORAGE | MARKET | RESEARCH | NETWORK
## Locked sections are visible with a lock indicator (not hidden).
## RESEARCH is locked until progression gate is met (communicated by server).

extends Control
class_name GmnNavBar

## Emitted when user selects a nav section. surface_id: one of NAV_SECTIONS.
signal surface_selected(surface_id: String)

const NAV_SECTIONS := ["MINE", "HARDWARE", "POWER", "STORAGE", "MARKET", "RESEARCH", "NETWORK"]
## Sections locked by default until server signals unlock.
const INITIALLY_LOCKED := ["RESEARCH"]

var _active_section: String = "MINE"
var _locked_sections: Array[String] = []
var _buttons: Dictionary = {}  ## section_id → Button

func _ready() -> void:
	_locked_sections.assign(INITIALLY_LOCKED)
	_build_nav()

## Unlock a section (called when server confirms progression gate passed).
func unlock_section(section_id: String) -> void:
	_locked_sections.erase(section_id.to_upper())
	_update_button_states()

## Lock a section.
func lock_section(section_id: String) -> void:
	var upper := section_id.to_upper()
	if upper not in _locked_sections:
		_locked_sections.append(upper)
	_update_button_states()

## Programmatically activate a section (e.g. after scene load).
func select_section(section_id: String) -> void:
	var upper := section_id.to_upper()
	if upper in NAV_SECTIONS and upper not in _locked_sections:
		_active_section = upper
		_update_button_states()
		surface_selected.emit(upper)

func get_active_section() -> String:
	return _active_section

func _build_nav() -> void:
	var hbox := HBoxContainer.new()
	hbox.alignment = BoxContainer.ALIGNMENT_BEGIN
	add_child(hbox)

	for section in NAV_SECTIONS:
		var btn := Button.new()
		btn.text = section
		btn.focus_mode = Control.FOCUS_ALL
		_buttons[section] = btn
		hbox.add_child(btn)
		var section_captured: String = section
		btn.pressed.connect(func() -> void: _on_section_pressed(section_captured))

	_update_button_states()
	_enforce_focus_ring()

func _on_section_pressed(section_id: String) -> void:
	if section_id in _locked_sections:
		return
	_active_section = section_id
	_update_button_states()
	surface_selected.emit(section_id)

func _update_button_states() -> void:
	for section in NAV_SECTIONS:
		var btn: Button = _buttons.get(section)
		if btn == null:
			continue
		var locked: bool = section in _locked_sections
		var active: bool = section == _active_section
		btn.disabled = locked
		btn.text = ("🔒 %s" % section) if locked else section
		if active:
			btn.add_theme_color_override("font_color", GmnUiTokens.ACCENT_PRIMARY)
		else:
			btn.remove_theme_color_override("font_color")

func get_first_focusable() -> Control:
	return _buttons.get(NAV_SECTIONS[0])

func get_last_focusable() -> Control:
	return _buttons.get(NAV_SECTIONS[NAV_SECTIONS.size() - 1])

func _enforce_focus_ring() -> void:
	for i in range(NAV_SECTIONS.size()):
		var section := NAV_SECTIONS[i]
		var btn: Button = _buttons.get(section)
		if btn == null:
			continue
		var left_section := NAV_SECTIONS[(i - 1 + NAV_SECTIONS.size()) % NAV_SECTIONS.size()]
		var right_section := NAV_SECTIONS[(i + 1) % NAV_SECTIONS.size()]
		var left_btn: Button = _buttons.get(left_section)
		var right_btn: Button = _buttons.get(right_section)
		if left_btn:
			btn.focus_neighbor_left = btn.get_path_to(left_btn)
		if right_btn:
			btn.focus_neighbor_right = btn.get_path_to(right_btn)
