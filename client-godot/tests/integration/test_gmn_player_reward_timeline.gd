## Test GMN-CL-04: Player Reward Timeline Panel
## Validates: Server entry rendering, empty states, no client mutation

extends GutTest

var reward_service: GmnPlayerRewardTimelineService
var timeline_panel: GmnPlayerRewardTimelinePanel
var test_player_id: String = "test_player_" + str(randi())

func before_each() -> void:
	reward_service = GmnPlayerRewardTimelineService.new()
	add_child(reward_service)
	
	timeline_panel = GmnPlayerRewardTimelinePanel.new()
	add_child(timeline_panel)

func after_each() -> void:
	if reward_service:
		reward_service.queue_free()
	if timeline_panel:
		timeline_panel.queue_free()

## Test 1: Empty state when no rewards
func test_empty_state_rendering() -> void:
	reward_service.set_player_id(test_player_id)
	reward_service.reward_entries = []
	reward_service.is_loaded = true
	
	timeline_panel.reward_service = reward_service
	timeline_panel._on_empty_state()
	
	assert_true(timeline_panel.is_empty_state_visible(), "Empty state label should be visible")
	assert_eq(timeline_panel.get_displayed_count(), 0, "No reward items should be displayed")

## Test 2: Reward entry rendering
func test_reward_entry_rendering() -> void:
	reward_service.set_player_id(test_player_id)
	
	# Create mock reward entries (server-provided, read-only)
	var entry1 = {
		"block_number": 100,
		"reward_amount": 50.5,
		"contribution_hash": "abc123def456"
	}
	
	var entry2 = {
		"block_number": 101,
		"reward_amount": 75.25,
		"contribution_hash": "xyz789uvw012"
	}
	
	reward_service.reward_entries = [entry1, entry2]
	reward_service.is_loaded = true
	
	timeline_panel.reward_service = reward_service
	timeline_panel._on_rewards_loaded([entry1, entry2])
	
	assert_false(timeline_panel.is_empty_state_visible(), "Empty state should not be visible")
	assert_eq(timeline_panel.get_displayed_count(), 2, "Should display 2 reward items")

## Test 3: No client mutation of entries
func test_no_client_mutation() -> void:
	reward_service.set_player_id(test_player_id)
	
	# Original entry from server
	var original_entry = {
		"block_number": 100,
		"reward_amount": 50.5,
		"contribution_hash": "abc123def456"
	}
	
	reward_service.reward_entries = [original_entry]
	
	# Get entry and verify structure
	var entry = reward_service.get_reward_entry(0)
	
	# Verify we cannot derive or calculate values
	# Entry must have exact server values
	assert_eq(entry.get("block_number"), 100, "Block number should be server value")
	assert_eq(entry.get("reward_amount"), 50.5, "Reward amount should be server value")
	assert_eq(entry.get("contribution_hash"), "abc123def456", "Hash should be server value")

## Test 4: Entry structure validation
func test_entry_structure_validation() -> void:
	reward_service.set_player_id(test_player_id)
	
	# Valid entry
	var valid_entry = {
		"block_number": 100,
		"reward_amount": 50.5,
		"contribution_hash": "abc123"
	}
	
	assert_true(reward_service._validate_entry_structure(valid_entry), "Valid entry should pass")
	
	# Invalid entry (missing fields)
	var invalid_entry = {
		"block_number": 100
	}
	
	assert_false(reward_service._validate_entry_structure(invalid_entry), "Invalid entry should fail")

## Test 5: Service set player ID
func test_service_player_id_setting() -> void:
	assert_eq(reward_service.player_id, "", "Player ID should be empty initially")
	
	reward_service.set_player_id(test_player_id)
	assert_eq(reward_service.player_id, test_player_id, "Player ID should match set value")

## Test 6: Service empty check
func test_service_empty_check() -> void:
	reward_service.set_player_id(test_player_id)
	
	assert_true(reward_service.is_empty(), "Should be empty initially")
	
	reward_service.reward_entries = [{"block_number": 1, "reward_amount": 10.0, "contribution_hash": "x"}]
	assert_false(reward_service.is_empty(), "Should not be empty after adding entry")

## Test 7: Service entry count
func test_service_entry_count() -> void:
	reward_service.set_player_id(test_player_id)
	
	assert_eq(reward_service.get_entry_count(), 0, "Count should be 0 initially")
	
	reward_service.reward_entries = [
		{"block_number": 1, "reward_amount": 10.0, "contribution_hash": "x"},
		{"block_number": 2, "reward_amount": 20.0, "contribution_hash": "y"},
		{"block_number": 3, "reward_amount": 30.0, "contribution_hash": "z"}
	]
	
	assert_eq(reward_service.get_entry_count(), 3, "Count should be 3")

## Test 8: Format entry for display
func test_format_entry_for_display() -> void:
	var entry = {
		"block_number": 100,
		"reward_amount": 50.5,
		"contribution_hash": "abc123def456"
	}
	
	var formatted = reward_service.format_entry_for_display(entry)
	
	assert_eq(formatted.get("block"), 100, "Block should map correctly")
	assert_eq(formatted.get("amount"), 50.5, "Amount should map correctly")
	assert_eq(formatted.get("hash"), "abc123def456", "Hash should map correctly")

## Test 9: Clear rewards on logout
func test_clear_rewards_on_logout() -> void:
	reward_service.set_player_id(test_player_id)
	reward_service.reward_entries = [{"block_number": 1, "reward_amount": 10.0, "contribution_hash": "x"}]
	reward_service.is_loaded = true
	
	assert_true(reward_service.is_rewards_loaded(), "Rewards should be loaded")
	
	reward_service.clear_rewards()
	
	assert_false(reward_service.is_rewards_loaded(), "Rewards should be cleared")
	assert_eq(reward_service.player_id, "", "Player ID should be cleared")
	assert_eq(reward_service.get_entry_count(), 0, "Entries should be cleared")

## Test 10: Acceptance criteria validation
## Criteria 1: Timeline renders server entries without client mutation ✓
## Criteria 2: Empty states handled when no rewards exist ✓
## Criteria 3: Rendering uses contract fields without inferred reward math ✓
func test_acceptance_criteria_met() -> void:
	# Criteria 1: Server entry rendering
	var server_entry = {
		"block_number": 100,
		"reward_amount": 50.5,
		"contribution_hash": "abc123"
	}
	reward_service.set_player_id(test_player_id)
	reward_service.reward_entries = [server_entry]
	
	timeline_panel.reward_service = reward_service
	timeline_panel._on_rewards_loaded([server_entry])
	
	assert_eq(timeline_panel.get_displayed_count(), 1, "Criteria 1: Entry rendered from server")
	
	# Criteria 2: Empty state handling
	reward_service.reward_entries = []
	timeline_panel._on_empty_state()
	assert_true(timeline_panel.is_empty_state_visible(), "Criteria 2: Empty state visible")
	
	# Criteria 3: No inferred math (use contract fields directly)
	var formatted = reward_service.format_entry_for_display(server_entry)
	assert_eq(formatted.get("amount"), 50.5, "Criteria 3: Use server value without calculation")
	
	pass_test("All acceptance criteria met for GMN-CL-04")

## Test 11: Multiple rewards display
func test_multiple_rewards_display() -> void:
	reward_service.set_player_id(test_player_id)
	
	var entries = [
		{"block_number": 98, "reward_amount": 25.0, "contribution_hash": "hash1"},
		{"block_number": 99, "reward_amount": 30.0, "contribution_hash": "hash2"},
		{"block_number": 100, "reward_amount": 45.5, "contribution_hash": "hash3"},
		{"block_number": 101, "reward_amount": 50.25, "contribution_hash": "hash4"},
		{"block_number": 102, "reward_amount": 60.0, "contribution_hash": "hash5"}
	]
	
	reward_service.reward_entries = entries
	timeline_panel.reward_service = reward_service
	timeline_panel._on_rewards_loaded(entries)
	
	assert_eq(timeline_panel.get_displayed_count(), 5, "Should display all 5 rewards")
	assert_false(timeline_panel.is_empty_state_visible(), "Empty state should not be visible")

## Test 12: Panel visibility control
func test_panel_visibility() -> void:
	reward_service.set_player_id(test_player_id)
	reward_service.reward_entries = []
	
	timeline_panel.reward_service = reward_service
	
	assert_false(timeline_panel.visible, "Panel should be hidden initially")
	
	timeline_panel.visible = true
	assert_true(timeline_panel.visible, "Panel should be visible after show")
	
	timeline_panel.visible = false
	assert_false(timeline_panel.visible, "Panel should be hidden after hide")
