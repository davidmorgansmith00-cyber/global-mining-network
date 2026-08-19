## GMN Global Block Header
## Dominant persistent top-of-screen element. Full width. Always visible.
## All displayed values are server-authoritative from BlockStatus.
## Client NEVER derives block progress, difficulty, or hashrate locally.

extends Control
class_name GmnGlobalBlockHeader

## Source: BlockStatus.block_number
@export var block_number_label_path: NodePath
## Source: BlockStatus.difficulty
@export var difficulty_label_path: NodePath
## Source: BlockStatus.global_hashrate
@export var global_hashrate_label_path: NodePath
## Source: BlockStatus.progress (server-provided %)
@export var progress_bar_path: NodePath
## Source: BlockStatus.state
@export var state_label_path: NodePath

@onready var _block_number_label: Label    = get_node_or_null(block_number_label_path)
@onready var _difficulty_label: Label      = get_node_or_null(difficulty_label_path)
@onready var _global_hashrate_label: Label = get_node_or_null(global_hashrate_label_path)
@onready var _progress_bar: ProgressBar    = get_node_or_null(progress_bar_path)
@onready var _state_label: Label           = get_node_or_null(state_label_path)

## Update all fields from server-provided BlockStatus payload.
## Never called with locally-computed values.
func update_from_block_status(payload: Dictionary) -> void:
	var active: Dictionary = payload.get("active_block", payload) as Dictionary
	var block_number: int = int(active.get("block_number", 0))
	var difficulty: float = float(active.get("difficulty", 0.0))
	var global_hashrate: float = float(
		payload.get("global_hashrate", active.get("global_hashrate", 0.0))
	)
	var progress: float = float(active.get("progress_percent", 0.0))
	var state: String = str(active.get("state", "unknown"))

	if _block_number_label:
		_block_number_label.text = "BLOCK #%d" % block_number
	if _difficulty_label:
		_difficulty_label.text = "DIFFICULTY %.2f TH" % (difficulty / 1_000_000_000_000.0) \
			if difficulty >= 1_000_000_000_000.0 else "DIFFICULTY %.2f" % difficulty
	if _global_hashrate_label:
		_global_hashrate_label.text = _format_hashrate(global_hashrate)
	if _progress_bar:
		_progress_bar.value = clampf(progress, 0.0, 100.0)
	if _state_label:
		_state_label.text = state.to_upper()

## Applies the token palette colours to child nodes, called once in _ready.
func apply_token_colours() -> void:
	if _block_number_label:
		_block_number_label.add_theme_color_override("font_color", GmnUiTokens.TEXT_PRIMARY)
	if _difficulty_label:
		_difficulty_label.add_theme_color_override("font_color", GmnUiTokens.TEXT_SECONDARY)
	if _global_hashrate_label:
		_global_hashrate_label.add_theme_color_override("font_color", GmnUiTokens.ACCENT_PRIMARY)
	if _state_label:
		_state_label.add_theme_color_override("font_color", GmnUiTokens.ACCENT_SUCCESS)

func _ready() -> void:
	apply_token_colours()

## Format a raw hashrate (hashes/s) into a human-readable string.
func _format_hashrate(hps: float) -> String:
	if hps >= 1_000_000_000_000_000.0:
		return "GLOBAL %.1f PH/s" % (hps / 1_000_000_000_000_000.0)
	if hps >= 1_000_000_000_000.0:
		return "GLOBAL %.1f TH/s" % (hps / 1_000_000_000_000.0)
	if hps >= 1_000_000_000.0:
		return "GLOBAL %.1f GH/s" % (hps / 1_000_000_000.0)
	if hps >= 1_000_000.0:
		return "GLOBAL %.1f MH/s" % (hps / 1_000_000.0)
	return "GLOBAL %.1f KH/s" % (hps / 1_000.0)
