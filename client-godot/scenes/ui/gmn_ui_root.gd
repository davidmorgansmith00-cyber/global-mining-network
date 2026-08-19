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
@onready var pause_overlay: ColorRect       = $ModalLayer/PauseOverlay
@onready var pause_settings_button: Button  = $ModalLayer/PauseOverlay/PausePanel/SettingsButton
@onready var pause_resume_button: Button     = $ModalLayer/PauseOverlay/PausePanel/ResumeButton
@onready var pause_close_button: Button      = $ModalLayer/PauseOverlay/PausePanel/CloseButton

var _reduce_motion_enabled := false

func _ready() -> void:
	_apply_layer_ordering()
	debug_layer.visible = false
	pause_resume_button.pressed.connect(_close_pause)
	pause_close_button.pressed.connect(_close_pause)
	pause_settings_button.pressed.connect(_toggle_reduce_motion)

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("debug_toggle"):
		debug_layer.visible = not debug_layer.visible
		return
	if event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		pause_overlay.visible = not pause_overlay.visible
		get_viewport().set_input_as_handled()

func _close_pause() -> void:
	pause_overlay.visible = false

func _toggle_reduce_motion() -> void:
	_reduce_motion_enabled = not _reduce_motion_enabled
	pause_settings_button.text = "REDUCE MOTION: ON" if _reduce_motion_enabled else "REDUCE MOTION: OFF"

func _apply_layer_ordering() -> void:
	background_layer.layer   = 0
	hud_layer.layer          = 10
	modal_layer.layer        = 20
	notification_layer.layer = 30
	debug_layer.layer        = 99
