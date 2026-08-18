extends RefCounted
class_name GmnAccessibilitySettings

const MIN_SCALE := 0.75
const MAX_SCALE := 2.0
const COLOR_MODES := ["none", "deuteranopia", "protanopia"]

var ui_scale: float = 1.0
var text_scale: float = 1.0
var high_contrast: bool = false
var color_mode: String = "none"
var reduce_motion: bool = false

func set_ui_scale(value: float) -> void:
	ui_scale = clampf(value, MIN_SCALE, MAX_SCALE)

func set_text_scale(value: float) -> void:
	text_scale = clampf(value, MIN_SCALE, MAX_SCALE)

func set_color_mode(value: String) -> void:
	color_mode = value if value in COLOR_MODES else "none"

func toggle_reduce_motion() -> void:
	reduce_motion = not reduce_motion

func to_display() -> Dictionary:
	return {
		"ui_scale": ui_scale,
		"text_scale": text_scale,
		"high_contrast": high_contrast,
		"color_mode": color_mode,
		"reduce_motion": reduce_motion,
	}
