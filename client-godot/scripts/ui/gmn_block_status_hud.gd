## GMN Block Status HUD
## Displays authoritative blockchain status (server-provided only)
## Never derives progression values locally

class_name GmnBlockStatusHud
extends Control

## Display fields
@onready var block_number_label: Label = Label.new()
@onready var accumulated_work_label: Label = Label.new()
@onready var required_work_label: Label = Label.new()
@onready var progress_bar: ProgressBar = ProgressBar.new()
@onready var status_text: Label = Label.new()

## Current status data (server-provided only)
var current_block_number: int = 0
var current_accumulated_work: float = 0.0
var current_required_work: float = 0.0
var current_progress_percent: float = 0.0
var current_finalized_blocks: int = 0

func _ready() -> void:
	# Setup labels
	block_number_label.text = "Block: 0"
	accumulated_work_label.text = "Accumulated Work: 0.0 hps"
	required_work_label.text = "Required Work: 0.0 hps"
	progress_bar.value = 0
	progress_bar.max_value = 100
	status_text.text = "Status: Connecting..."
	
	add_child(block_number_label)
	add_child(accumulated_work_label)
	add_child(required_work_label)
	add_child(progress_bar)
	add_child(status_text)

## Update HUD from authoritative status response
## Never derives values locally - only displays server-provided data
func update_from_status(status_response: Dictionary) -> void:
	if not status_response.get("ok", false):
		status_text.text = "Status: Error fetching data"
		return
	
	var payload = status_response.get("payload", {})
	
	# Extract authoritative values from server response
	var block_data = payload.get("active_block", {})
	current_block_number = int(block_data.get("block_number", 0))
	current_accumulated_work = float(block_data.get("accumulated_work", 0.0))
	current_required_work = float(block_data.get("required_work", 0.0))
	current_finalized_blocks = int(payload.get("finalized_blocks", 0))
	
	# Calculate progress as server-provided value if available
	# Otherwise derive from accumulated vs required (only for display)
	if block_data.has("progress_percent"):
		current_progress_percent = float(block_data.get("progress_percent", 0.0))
	elif current_required_work > 0:
		current_progress_percent = (current_accumulated_work / current_required_work) * 100.0
	else:
		current_progress_percent = 0.0
	
	# Cap progress at 100%
	current_progress_percent = min(current_progress_percent, 100.0)
	
	# Update display
	_refresh_display()

## Refresh display from current data
func _refresh_display() -> void:
	block_number_label.text = "Block: %d" % current_block_number
	accumulated_work_label.text = "Accumulated Work: %.2f hps" % current_accumulated_work
	required_work_label.text = "Required Work: %.2f hps" % current_required_work
	progress_bar.value = int(current_progress_percent)
	status_text.text = "Status: Block %d (%.1f%%)" % [current_block_number, current_progress_percent]

## Get current status (read-only)
func get_current_block_number() -> int:
	return current_block_number

func get_current_accumulated_work() -> float:
	return current_accumulated_work

func get_current_required_work() -> float:
	return current_required_work

func get_current_progress_percent() -> float:
	return current_progress_percent

func get_finalized_blocks() -> int:
	return current_finalized_blocks
