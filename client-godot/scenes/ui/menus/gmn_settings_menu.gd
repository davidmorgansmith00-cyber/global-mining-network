## GMN Settings Menu
## Tabs: Video / Audio / Input / Gameplay.
## Delegates accessibility changes through GmnAccessibilitySettings.
extends Control
class_name GmnSettingsMenu

signal closed

var _tab_bar: GmnTabBar
var _ui_scale_label: Label
var _text_scale_label: Label
var _close_button: GmnButton
var _settings := GmnAccessibilitySettings.new()

func _ready() -> void:
	var layout := VBoxContainer.new()
	layout.anchor_left = 0.5
	layout.anchor_top = 0.5
	layout.anchor_right = 0.5
	layout.anchor_bottom = 0.5
	layout.offset_left = -220.0
	layout.offset_top = -170.0
	layout.offset_right = 220.0
	layout.offset_bottom = 170.0
	layout.add_theme_constant_override("separation", 12)
	add_child(layout)

	_tab_bar = GmnTabBar.new()
	_tab_bar.tabs = PackedStringArray(["VIDEO", "AUDIO", "INPUT", "GAMEPLAY"])
	layout.add_child(_tab_bar)

	_ui_scale_label = Label.new()
	_text_scale_label = Label.new()
	layout.add_child(_ui_scale_label)
	layout.add_child(_text_scale_label)

	var controls := HBoxContainer.new()
	layout.add_child(controls)
	var ui_down := GmnButton.new()
	ui_down.text = "UI -"
	ui_down.variant = "ghost"
	var ui_up := GmnButton.new()
	ui_up.text = "UI +"
	ui_up.variant = "ghost"
	var text_down := GmnButton.new()
	text_down.text = "TEXT -"
	text_down.variant = "ghost"
	var text_up := GmnButton.new()
	text_up.text = "TEXT +"
	text_up.variant = "ghost"
	controls.add_child(ui_down)
	controls.add_child(ui_up)
	controls.add_child(text_down)
	controls.add_child(text_up)

	_close_button = GmnButton.new()
	_close_button.text = "CLOSE"
	_close_button.variant = "secondary"
	layout.add_child(_close_button)

	ui_down.pressed.connect(func() -> void: _settings.set_ui_scale(_settings.ui_scale - 0.25); _refresh_labels())
	ui_up.pressed.connect(func() -> void: _settings.set_ui_scale(_settings.ui_scale + 0.25); _refresh_labels())
	text_down.pressed.connect(func() -> void: _settings.set_text_scale(_settings.text_scale - 0.25); _refresh_labels())
	text_up.pressed.connect(func() -> void: _settings.set_text_scale(_settings.text_scale + 0.25); _refresh_labels())
	_close_button.pressed.connect(func() -> void: closed.emit())
	_refresh_labels()

func _refresh_labels() -> void:
	_ui_scale_label.text = "UI SCALE: %.2fx" % _settings.ui_scale
	_text_scale_label.text = "TEXT SCALE: %.2fx" % _settings.text_scale
