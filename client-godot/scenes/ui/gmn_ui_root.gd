## GMN UIRoot scene root script.
## Owns the five canonical UI layers: BackgroundLayer → HUDLayer → ModalLayer
## → NotificationLayer → DebugLayer.
## debug_toggle (backtick key, configurable in project.godot) shows/hides DebugLayer.
## World scene WorldRoot must be parented under BackgroundLayer at runtime.
## UIStateController integration is [planned — not yet implemented]; authoritative
## state is currently delivered through GameplayShellController.

extends Control
class_name GmnUIRoot

@onready var background_layer: CanvasLayer  = $BackgroundLayer
@onready var hud_layer: CanvasLayer         = $HUDLayer
@onready var modal_layer: CanvasLayer       = $ModalLayer
@onready var notification_layer: CanvasLayer = $NotificationLayer
@onready var debug_layer: CanvasLayer       = $DebugLayer

func _ready() -> void:
	_apply_layer_ordering()
	debug_layer.visible = false

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("debug_toggle"):
		debug_layer.visible = not debug_layer.visible

func _apply_layer_ordering() -> void:
	background_layer.layer   = 0
	hud_layer.layer          = 10
	modal_layer.layer        = 20
	notification_layer.layer = 30
	debug_layer.layer        = 99
