## GMN Progress Bar
## Includes a delayed-damage layer and threshold colours (green→amber→red).
extends Control
class_name GmnProgressBar

@export var max_value: float = 100.0:
	set(v):
		max_value = maxf(1.0, v)
		_refresh()

@export var value: float = 0.0:
	set(v):
		value = clampf(v, 0.0, max_value)
		if delayed_value < value:
			delayed_value = value
		_refresh()

@export var delayed_value: float = 0.0:
	set(v):
		delayed_value = clampf(v, 0.0, max_value)
		_refresh()

var _delayed_bar: ProgressBar
var _main_bar: ProgressBar

func _ready() -> void:
	_delayed_bar = ProgressBar.new()
	_main_bar = ProgressBar.new()
	for bar in [_delayed_bar, _main_bar]:
		bar.min_value = 0.0
		bar.max_value = max_value
		bar.show_percentage = false
		bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		bar.size_flags_vertical = Control.SIZE_EXPAND_FILL
		bar.anchor_right = 1.0
		bar.anchor_bottom = 1.0
		bar.offset_right = 0.0
		bar.offset_bottom = 0.0
		add_child(bar)
	_refresh()

func set_value_with_delay(next_value: float) -> void:
	var clamped := clampf(next_value, 0.0, max_value)
	if clamped < value:
		delayed_value = value
	value = clamped
	_refresh()

func _refresh() -> void:
	if _main_bar == null or _delayed_bar == null:
		return
	_main_bar.max_value = max_value
	_delayed_bar.max_value = max_value
	_main_bar.value = value
	_delayed_bar.value = max(delayed_value, value)
	_apply_style(_main_bar, _threshold_colour())
	_apply_style(_delayed_bar, Color(GmnUiTokens.ACCENT_DANGER.r, GmnUiTokens.ACCENT_DANGER.g, GmnUiTokens.ACCENT_DANGER.b, 0.40))

func _apply_style(bar: ProgressBar, fill_colour: Color) -> void:
	var background := StyleBoxFlat.new()
	background.bg_color = GmnUiTokens.BG_PANEL_ALT
	background.corner_radius_top_left = 6
	background.corner_radius_top_right = 6
	background.corner_radius_bottom_left = 6
	background.corner_radius_bottom_right = 6
	bar.add_theme_stylebox_override("background", background)
	var fill := StyleBoxFlat.new()
	fill.bg_color = fill_colour
	fill.corner_radius_top_left = 6
	fill.corner_radius_top_right = 6
	fill.corner_radius_bottom_left = 6
	fill.corner_radius_bottom_right = 6
	bar.add_theme_stylebox_override("fill", fill)

func _threshold_colour() -> Color:
	var ratio := value / max_value
	if ratio >= 0.67:
		return GmnUiTokens.ACCENT_SUCCESS
	if ratio >= 0.34:
		return GmnUiTokens.ACCENT_WARNING
	return GmnUiTokens.ACCENT_DANGER
