## GMN Player Reward Timeline Panel UI
## Renders server reward entries without client mutation

extends Control
class_name GmnPlayerRewardTimelinePanel

## UI references
@onready var timeline_container = $VBoxContainer/ScrollContainer/TimelineVBox
@onready var empty_state_label = $VBoxContainer/EmptyStateLabel
@onready var scroll_container = $VBoxContainer/ScrollContainer

## Reward service reference
var reward_service: GmnPlayerRewardTimelineService = null

## UI state
var is_visible_panel: bool = false

func _ready() -> void:
	reward_service = get_parent().get_node("GmnPlayerRewardTimelineService") if get_parent() != null else null
	
	# Connect to reward service signals
	if reward_service:
		reward_service.rewards_loaded.connect(_on_rewards_loaded)
		reward_service.empty_state_reached.connect(_on_empty_state)
		reward_service.fetch_error.connect(_on_fetch_error)
	
	# Hide initially
	visible = false
	empty_state_label.visible = false

## Show panel and load rewards
func show_panel() -> void:
	is_visible_panel = true
	visible = true
	
	# Fetch rewards from service
	if reward_service:
		await reward_service.fetch_rewards()

## Hide panel
func hide_panel() -> void:
	is_visible_panel = false
	visible = false

## Handle rewards loaded signal
func _on_rewards_loaded(entries: Array) -> void:
	empty_state_label.visible = false
	_render_timeline(entries)

## Handle empty state signal
func _on_empty_state() -> void:
	timeline_container.clear()
	empty_state_label.visible = true
	empty_state_label.text = "No rewards yet. Keep mining to earn rewards!"

## Handle fetch error
func _on_fetch_error(error: String) -> void:
	empty_state_label.visible = true
	empty_state_label.text = "Error loading rewards: " + error

## Render timeline entries (no client mutation, server values only)
func _render_timeline(entries: Array) -> void:
	# Clear existing entries
	timeline_container.clear()
	
	# Render each entry
	for i in range(entries.size()):
		var entry = entries[i]
		_add_entry_item(i, entry)

## Add individual entry to timeline
func _add_entry_item(index: int, entry: Dictionary) -> void:
	# Create entry container
	var entry_container = PanelContainer.new()
	entry_container.add_theme_stylebox_override("panel", preload("res://styles/entry_panel.tres"))
	
	# Create content vbox
	var content_vbox = VBoxContainer.new()
	entry_container.add_child(content_vbox)
	
	# Block number label
	var block_label = Label.new()
	block_label.text = "Block: %d" % entry.get("block_number", 0)
	block_label.add_theme_font_size_override("font_size", 14)
	content_vbox.add_child(block_label)
	
	# Reward amount label
	var reward_label = Label.new()
	reward_label.text = "Reward: %f" % entry.get("reward_amount", 0.0)
	reward_label.add_theme_color_override("font_color", Color.LIGHT_GREEN)
	content_vbox.add_child(reward_label)
	
	# Contribution hash label (truncated for display)
	var hash_label = Label.new()
	var full_hash = entry.get("contribution_hash", "")
	var display_hash = full_hash.substr(0, 16) + "..." if full_hash.length() > 16 else full_hash
	hash_label.text = "Hash: %s" % display_hash
	hash_label.add_theme_font_size_override("font_size", 11)
	hash_label.add_theme_color_override("font_color", Color.GRAY)
	content_vbox.add_child(hash_label)
	
	# Add to timeline
	timeline_container.add_child(entry_container)

## Get current reward count (for testing)
func get_displayed_count() -> int:
	return timeline_container.get_child_count()

## Check if empty state is visible (for testing)
func is_empty_state_visible() -> bool:
	return empty_state_label.visible
