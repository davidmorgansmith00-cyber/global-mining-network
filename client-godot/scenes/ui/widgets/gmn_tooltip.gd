## GMN Tooltip
## Hover-activated tooltip with 0.25s delay and 320px max width.
extends PanelContainer
class_name GmnTooltip

@export var hover_delay_seconds: float = 0.25
@export var max_tooltip_width: float = 320.0
@export_multiline var tooltip_text: String = "":
	set(value):
		tooltip_text = value
		if _label:
			_label.text = value

var _label: Label
var _show_ticket: int = 0

func _ready() -> void:
	visible = false
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_label = Label.new()
	_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_label.custom_minimum_size = Vector2(max_tooltip_width, 0.0)
	_label.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	_label.add_theme_color_override("font_color", GmnUiTokens.TEXT_PRIMARY)
	_label.text = tooltip_text
	add_child(_label)
	var style := StyleBoxFlat.new()
	style.bg_color = GmnUiTokens.BG_PANEL_ALT
	style.border_color = GmnUiTokens.LINE_SUBTLE
	style.border_width_left = 1
	style.border_width_top = 1
	style.border_width_right = 1
	style.border_width_bottom = 1
	style.corner_radius_top_left = 6
	style.corner_radius_top_right = 6
	style.corner_radius_bottom_left = 6
	style.corner_radius_bottom_right = 6
	add_theme_stylebox_override("panel", style)

func show_with_delay(next_text: String = "") -> void:
	if next_text != "":
		tooltip_text = next_text
	_show_ticket += 1
	var ticket := _show_ticket
	if hover_delay_seconds <= 0.0:
		visible = true
		return
	await get_tree().create_timer(hover_delay_seconds).timeout
	if ticket == _show_ticket:
		visible = true

func hide_tooltip() -> void:
	_show_ticket += 1
	visible = false
