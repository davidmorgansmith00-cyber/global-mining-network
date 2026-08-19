## GMN Panel
## Tokenised container with header/body/footer slots.
extends PanelContainer
class_name GmnPanel

const VARIANTS := ["solid", "glass", "outline"]

@export var variant: String = "solid":
	set(value):
		variant = value.to_lower() if value.to_lower() in VARIANTS else "solid"
		_apply_panel_style()

var header_slot: HBoxContainer
var body_slot: VBoxContainer
var footer_slot: HBoxContainer

func _ready() -> void:
	_ensure_slots()
	_apply_panel_style()

func _ensure_slots() -> void:
	if get_child_count() > 0 and get_child(0) is VBoxContainer and get_child(0).name == "SlotRoot":
		var slot_root: VBoxContainer = get_child(0)
		header_slot = slot_root.get_node("Header")
		body_slot = slot_root.get_node("Body")
		footer_slot = slot_root.get_node("Footer")
		return
	var root := VBoxContainer.new()
	root.name = "SlotRoot"
	root.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	root.size_flags_vertical = Control.SIZE_EXPAND_FILL
	add_child(root)
	header_slot = HBoxContainer.new()
	header_slot.name = "Header"
	body_slot = VBoxContainer.new()
	body_slot.name = "Body"
	body_slot.size_flags_vertical = Control.SIZE_EXPAND_FILL
	footer_slot = HBoxContainer.new()
	footer_slot.name = "Footer"
	root.add_child(header_slot)
	root.add_child(body_slot)
	root.add_child(footer_slot)

func _apply_panel_style() -> void:
	var style := StyleBoxFlat.new()
	style.corner_radius_top_left = 10
	style.corner_radius_top_right = 10
	style.corner_radius_bottom_left = 10
	style.corner_radius_bottom_right = 10
	match variant:
		"glass":
			style.bg_color = Color(0.102, 0.141, 0.188, 0.75)
			style.border_color = GmnUiTokens.ACCENT_PRIMARY
			style.border_width_left = 1
			style.border_width_top = 1
			style.border_width_right = 1
			style.border_width_bottom = 1
		"outline":
			style.bg_color = Color(0.043, 0.059, 0.078, 0.0)
			style.border_color = GmnUiTokens.LINE_SUBTLE
			style.border_width_left = 1
			style.border_width_top = 1
			style.border_width_right = 1
			style.border_width_bottom = 1
		_:
			style.bg_color = GmnUiTokens.BG_PANEL
			style.border_color = GmnUiTokens.LINE_SUBTLE
			style.border_width_left = 1
			style.border_width_top = 1
			style.border_width_right = 1
			style.border_width_bottom = 1
	add_theme_stylebox_override("panel", style)
