## GMN Stat Chip
## Compact key-value display widget (e.g. "HEAT  72.3°C").
## Used across HUD panels to present server-provided values uniformly.

extends HBoxContainer
class_name GmnStatChip

@export var label_text: String = "STAT":
	set(v): label_text = v; _refresh()
@export var value_text: String = "—":
	set(v): value_text = v; _refresh()

var _label_node: Label
var _value_node: Label

func _ready() -> void:
	_label_node = Label.new()
	_value_node = Label.new()
	add_child(_label_node)
	add_child(_value_node)
	_refresh()

func set_stat(label: String, value: String) -> void:
	label_text = label
	value_text = value

func _refresh() -> void:
	if _label_node:
		_label_node.text = label_text
		_label_node.add_theme_color_override("font_color", GmnUiTokens.TEXT_SECONDARY)
	if _value_node:
		_value_node.text = value_text
		_value_node.add_theme_color_override("font_color", GmnUiTokens.TEXT_PRIMARY)
