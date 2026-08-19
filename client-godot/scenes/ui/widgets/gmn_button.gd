## GMN Button
## Shared button with V2 token variants and explicit visual states.
extends Button
class_name GmnButton

const VARIANTS := ["primary", "secondary", "danger", "ghost"]
const STATES := ["default", "hover", "focus", "pressed", "disabled"]

@export var variant: String = "primary":
	set(value):
		variant = value.to_lower() if value.to_lower() in VARIANTS else "primary"
		_apply_style(_resolve_state())

func _ready() -> void:
	focus_mode = Control.FOCUS_ALL
	mouse_entered.connect(func() -> void: _apply_style("hover"))
	mouse_exited.connect(func() -> void: _apply_style(_resolve_state()))
	focus_entered.connect(func() -> void: _apply_style("focus"))
	focus_exited.connect(func() -> void: _apply_style(_resolve_state()))
	button_down.connect(func() -> void: _apply_style("pressed"))
	button_up.connect(func() -> void: _apply_style(_resolve_state()))
	_apply_style(_resolve_state())

func _notification(what: int) -> void:
	if what == NOTIFICATION_THEME_CHANGED or what == NOTIFICATION_VISIBILITY_CHANGED:
		_apply_style(_resolve_state())

func _resolve_state() -> String:
	if disabled:
		return "disabled"
	if button_pressed:
		return "pressed"
	if has_focus():
		return "focus"
	return "default"

func _apply_style(state: String) -> void:
	var palette := _state_palette(variant, state)
	add_theme_color_override("font_color", palette["font"])
	var style := StyleBoxFlat.new()
	style.bg_color = palette["background"]
	style.border_color = palette["border"]
	style.border_width_left = 1
	style.border_width_top = 1
	style.border_width_right = 1
	style.border_width_bottom = 1
	style.corner_radius_top_left = 6
	style.corner_radius_top_right = 6
	style.corner_radius_bottom_left = 6
	style.corner_radius_bottom_right = 6
	add_theme_stylebox_override("normal", style)
	add_theme_stylebox_override("hover", style)
	add_theme_stylebox_override("pressed", style)
	add_theme_stylebox_override("focus", style)
	add_theme_stylebox_override("disabled", style)

func _state_palette(variant_key: String, state: String) -> Dictionary:
	var bg := GmnUiTokens.BG_PANEL
	var border := GmnUiTokens.LINE_SUBTLE
	var font := GmnUiTokens.TEXT_PRIMARY
	match variant_key:
		"primary":
			bg = GmnUiTokens.ACCENT_PRIMARY
			border = GmnUiTokens.ACCENT_PRIMARY
			font = GmnUiTokens.BG_BASE
		"secondary":
			bg = GmnUiTokens.BG_PANEL_ALT
			border = GmnUiTokens.LINE_SUBTLE
			font = GmnUiTokens.TEXT_PRIMARY
		"danger":
			bg = GmnUiTokens.ACCENT_DANGER
			border = GmnUiTokens.ACCENT_DANGER
			font = GmnUiTokens.BG_BASE
		"ghost":
			bg = Color(GmnUiTokens.BG_BASE, 0.0)
			border = GmnUiTokens.LINE_SUBTLE
			font = GmnUiTokens.TEXT_PRIMARY
	if state == "hover":
		bg = bg.lightened(0.08)
	if state == "focus":
		border = GmnUiTokens.ACCENT_WARNING
	if state == "pressed":
		bg = bg.darkened(0.12)
	if state == "disabled":
		bg = Color(bg.r, bg.g, bg.b, 0.35)
		border = Color(border.r, border.g, border.b, 0.45)
		font = Color(font.r, font.g, font.b, 0.5)
	return {"background": bg, "border": border, "font": font}
