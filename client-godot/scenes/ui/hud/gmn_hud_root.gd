## GMN HUD Root
## Assembles all persistent HUD components in the correct visual hierarchy:
##   GlobalBlockHeader (top, dominant)
##   ResourceStrip     (below header)
##   PlayerOperationPanel (left panel)
##   PlayerVsNetworkPanel (centre)
##   GMNNavBar          (persistent bottom navigation)
##   NotificationFeed   (top-right overlay)
## Binds to GameplayShellController for all authoritative state.
## UIStateController integration is [planned — not yet implemented].

extends Control
class_name GmnHUDRoot

@export var controller_path: NodePath = NodePath("../GameplayShellController")

@onready var _global_block_header: GmnGlobalBlockHeader = $GlobalBlockHeader
@onready var _resource_strip: GmnResourceStrip          = $ResourceStrip
@onready var _player_op: GmnPlayerOperationPanel        = $PlayerOperationPanel
@onready var _vs_network: GmnPlayerVsNetworkPanel       = $PlayerVsNetworkPanel
@onready var _nav_bar: GmnNavBar                        = $GMNNavBar
@onready var _notifications: GmnNotificationFeed        = $NotificationFeed
@onready var _surface_title: Label                      = $SurfacePanel/SurfaceTitle
@onready var _surface_status: Label                     = $SurfacePanel/SurfaceStatus
@onready var _surface_hint: Label                       = $SurfacePanel/SurfaceHint
@onready var _surface_readout: Label                    = $SurfacePanel/SurfaceReadout
@onready var _operation_id_input: LineEdit              = $SurfacePanel/OperationIdInput
@onready var _start_operation_button: Button            = $SurfacePanel/StartOperationButton
@onready var _stop_operation_button: Button             = $SurfacePanel/StopOperationButton
@onready var _market_item_input: LineEdit                = $SurfacePanel/MarketItemInput
@onready var _market_quantity_input: LineEdit             = $SurfacePanel/MarketQuantityInput
@onready var _purchase_button: Button                    = $SurfacePanel/PurchaseButton
@onready var _surface_details: Label                    = $SurfacePanel/SurfaceDetails
@onready var _connection_state: Label                   = $ConnectionState
@onready var _sync_meta: Label                          = $SyncMeta

var _controller: GameplayShellController
var _action_in_progress := false
var _last_rendered_block_number := -1
var _last_rendered_reward_balance := -1.0

func _ready() -> void:
	_controller = get_node_or_null(controller_path)
	_nav_bar.surface_selected.connect(_on_surface_selected)
	_start_operation_button.pressed.connect(_on_start_operation_pressed)
	_stop_operation_button.pressed.connect(_on_stop_operation_pressed)
	_purchase_button.pressed.connect(_on_purchase_pressed)
	_on_surface_selected(_nav_bar.get_active_section())
	if _controller == null or _controller.session_id == "" or _controller.latest_status_payload.is_empty():
		_show_session_gate()
	_render_connection_state()
	if _controller != null and _controller.player_id != "" and _operation_id_input.text == "op_client_1":
		_operation_id_input.text = "op_%s" % _controller.player_id.left(8)
	_render_sync_meta()

## Call after GameplayShellController.refresh_authoritative_views() completes.
func refresh_from_controller() -> void:
	if _controller == null:
		return
	if _controller.player_id != "" and _operation_id_input.text == "op_client_1":
		_operation_id_input.text = "op_%s" % _controller.player_id.left(8)
	_render_connection_state()
	_render_sync_meta()
	if _controller.session_id == "" or _controller.latest_status_payload.is_empty():
		_show_session_gate()
		return
	if _controller.session_id != "" and not _action_in_progress:
		_set_action_busy(false)
	_on_surface_selected(_nav_bar.get_active_section())

	var status   := _controller.latest_status_payload
	var profile  := _controller.latest_profile_payload
	var snapshot := _controller.latest_snapshot_payload

	# Refresh global block header
	_global_block_header.update_from_block_status(status)
	var active_block_number := int(status.get("active_block_number", 0))
	if _last_rendered_block_number > 0 and active_block_number > _last_rendered_block_number:
		_notifications.push_critical("BLOCK #%d FINALIZED  NETWORK ADVANCED TO #%d" % [_last_rendered_block_number, active_block_number])
	_last_rendered_block_number = active_block_number

	# Refresh player operation panel — machine state from snapshot or status
	var machine_state: Dictionary = snapshot.get("machine_state", {}) as Dictionary
	if machine_state.is_empty():
		machine_state = profile.duplicate()
	if not _controller.latest_operation_payload.is_empty():
		machine_state["operation_status"] = str(_controller.latest_operation_payload.get("status", "idle"))
	_player_op.update_from_payloads(profile, machine_state)

	# Refresh player vs network
	var eff_hps := float(profile.get("effective_hashrate", machine_state.get("effective_hashrate", 0.0)))
	var global_hashrate: Variant = status.get("global_hashrate", null)
	var global_hps := float(global_hashrate) if global_hashrate != null else 0.0
	var contribution: Variant = machine_state.get("contribution_percent", null)
	_vs_network.update_from_payloads(eff_hps, global_hps, contribution)

	# Refresh resource strip
	var economy: Dictionary = profile.get("economy", profile) as Dictionary
	_resource_strip.update_from_payload(economy)
	var reward_balance := float(profile.get("reward_balance", 0.0))
	_resource_strip.update_from_payload({"reward_balance": reward_balance})
	if _last_rendered_reward_balance >= 0.0 and reward_balance > _last_rendered_reward_balance:
		_notifications.push_block_reward(reward_balance - _last_rendered_reward_balance)
	_last_rendered_reward_balance = reward_balance
	_render_surface(_nav_bar.get_active_section())
	_render_connection_state()

func _render_connection_state() -> void:
	if _connection_state == null:
		return
	if _controller == null or _controller.session_id == "":
		_connection_state.text = "NETWORK / SIGN IN REQUIRED"
		_connection_state.add_theme_color_override("font_color", GmnUiTokens.ACCENT_WARNING)
		return
	var state: Dictionary = _controller.get_ui_state()
	var state_code := str(state.get("state_code", GameplayShellUiState.LOADING)).to_upper()
	_connection_state.text = "NETWORK / %s" % state_code
	var colour := GmnUiTokens.ACCENT_PRIMARY
	if state_code == GameplayShellUiState.READY.to_upper():
		colour = GmnUiTokens.ACCENT_SUCCESS
	elif state_code == GameplayShellUiState.ERROR.to_upper() or state_code == GameplayShellUiState.UNAUTHORIZED.to_upper():
		colour = GmnUiTokens.ACCENT_DANGER
	elif state_code == GameplayShellUiState.STALE.to_upper() or state_code == GameplayShellUiState.MAINTENANCE.to_upper():
		colour = GmnUiTokens.ACCENT_WARNING
	_connection_state.add_theme_color_override("font_color", colour)

func _render_sync_meta() -> void:
	if _sync_meta == null or _controller == null:
		return
	var refreshed_at := _controller.last_authoritative_refresh_unix_seconds
	var cursor := _controller.stream_client.reconnect_cursor if _controller.stream_client != null else 0
	if refreshed_at <= 0:
		_sync_meta.text = "SYNC / WAITING FOR AUTHORITATIVE SNAPSHOT"
		return
	_sync_meta.text = "SYNC / LIVE   CURSOR %d   REFRESHED %s" % [cursor, Time.get_datetime_string_from_unix_time(refreshed_at)]

func handle_stream_message(message: Dictionary) -> void:
	var event_type := str(message.get("type", message.get("event_type", "network_event")))
	var payload: Dictionary = message.get("payload", message) as Dictionary
	var message_text := str(payload.get("message", message.get("message", "")))
	if message_text == "":
		message_text = event_type.replace("_", " ").capitalize()
	var priority := GmnNotificationFeed.Priority.INFORMATIONAL
	if event_type.contains("reward") or event_type.contains("final"):
		priority = GmnNotificationFeed.Priority.OPERATIONAL
	if event_type.contains("critical") or event_type.contains("maintenance"):
		priority = GmnNotificationFeed.Priority.CRITICAL
	_notifications.push(message_text, priority)

func _on_surface_selected(surface_id: String) -> void:
	var surface_copy: Array = {
		"MINE": ["MINE", "Operation control and network contribution"],
		"HARDWARE": ["HARDWARE", "Inspect your machine and available improvements"],
		"POWER": ["POWER", "Monitor facility capacity and server-reported throttling"],
		"STORAGE": ["STORAGE", "Review server-authoritative inventory and resources"],
		"MARKET": ["MARKET", "Browse the NPC market and submit purchase intents"],
		"RESEARCH": ["RESEARCH", "Progression surface locked until the network confirms access"],
		"NETWORK": ["NETWORK", "Explore the shared chain, pools, and network standings"],
	}.get(surface_id, [surface_id, "Surface awaiting server data"]) as Array
	_surface_title.text = str(surface_copy[0])
	_surface_status.text = str(surface_copy[1])
	_surface_hint.text = "Live authoritative data will appear here as this surface is connected."
	var mine_selected := surface_id == "MINE"
	_start_operation_button.visible = mine_selected
	_stop_operation_button.visible = mine_selected
	_operation_id_input.visible = mine_selected
	var market_selected := surface_id == "MARKET"
	_market_item_input.visible = market_selected
	_market_quantity_input.visible = market_selected
	_purchase_button.visible = market_selected
	_render_surface(surface_id)

func _show_session_gate() -> void:
	_surface_hint.text = "SIGN IN REQUIRED / NETWORK UNAVAILABLE  Return to onboarding and connect to the authoritative server."
	_surface_readout.text = "AUTHORITATIVE READOUT  No active session"
	_start_operation_button.disabled = true
	_stop_operation_button.disabled = true
	_purchase_button.disabled = true

func _on_start_operation_pressed() -> void:
	if _controller == null or _action_in_progress:
		return
	var operation_id := _operation_id_input.text.strip_edges()
	var base_hashrate := _controller.get_server_base_hashrate()
	if operation_id == "" or base_hashrate <= 0.0:
		_surface_hint.text = "Start rejected: session and server machine profile are required."
		return
	_set_action_busy(true)
	_surface_hint.text = "Submitting start intent to the server..."
	var response: Dictionary = await _controller.send_start_operation_intent(operation_id, base_hashrate)
	_surface_hint.text = "Start accepted by server." if response.get("ok", false) else "Start rejected by server."
	_set_action_busy(false)

func _on_stop_operation_pressed() -> void:
	if _controller == null or _action_in_progress:
		return
	var operation_id := _operation_id_input.text.strip_edges()
	if operation_id == "":
		_surface_hint.text = "Stop rejected: operation_id is required."
		return
	_set_action_busy(true)
	_surface_hint.text = "Submitting stop intent to the server..."
	var response: Dictionary = await _controller.send_stop_operation_intent(operation_id)
	_surface_hint.text = "Stop accepted by server." if response.get("ok", false) else "Stop rejected by server."
	_set_action_busy(false)

func _on_purchase_pressed() -> void:
	if _controller == null or _action_in_progress:
		return
	var item_id := _market_item_input.text.strip_edges()
	var quantity := int(_market_quantity_input.text)
	if item_id == "" or quantity <= 0:
		_surface_hint.text = "Purchase rejected: item_id and quantity are required."
		return
	_set_action_busy(true)
	_surface_hint.text = "Submitting purchase intent to the server..."
	var response: Dictionary = await _controller.send_market_purchase(item_id, quantity)
	_surface_hint.text = "Purchase accepted by server." if response.get("ok", false) else "Purchase rejected by server."
	_set_action_busy(false)

func _set_action_busy(busy: bool) -> void:
	_action_in_progress = busy
	_start_operation_button.disabled = busy
	_stop_operation_button.disabled = busy
	_purchase_button.disabled = busy

func _render_surface(surface_id: String) -> void:
	if _surface_readout == null:
		return
	if _controller == null:
		_surface_readout.text = "AUTHORITATIVE READOUT  Awaiting controller"
		return

	var profile: Dictionary = _controller.latest_profile_payload
	var status: Dictionary = _controller.latest_status_payload
	var snapshot: Dictionary = _controller.latest_snapshot_payload
	var blocks: Dictionary = _controller.latest_blocks_payload
	var events: Dictionary = _controller.latest_events_payload
	var pools: Dictionary = _controller.latest_pools_payload
	var leaderboard: Dictionary = _controller.latest_leaderboard_payload
	var position: Dictionary = _controller.latest_position_payload
	var machine: Dictionary = snapshot.get("machine_state", {}) as Dictionary
	var hardware: Dictionary = profile.get("hardware", profile) as Dictionary
	var economy: Dictionary = profile.get("economy", profile) as Dictionary
	var readout := "AUTHORITATIVE READOUT  Awaiting session data"
	_surface_details.text = "ADDITIONAL READ MODELS  Awaiting network sync"

	match surface_id:
		"MINE":
			readout = "STATUS  %s    EFFECTIVE HASHRATE  %s" % [
				str(machine.get("operation_status", "idle")).to_upper(),
				str(machine.get("effective_hashrate", profile.get("effective_hashrate", "—"))),
			]
			_surface_details.text = "OPERATION  %s    SERVER BASE HASHRATE  %s" % [
				str(machine.get("operation_status", "idle")).to_upper(),
				str(profile.get("base_hashrate", "—")),
			]
		"HARDWARE":
			readout = "MACHINE  %s    BASE HASHRATE  %s" % [
				str(hardware.get("name", profile.get("hardware_id", "—"))),
				str(hardware.get("base_hashrate", profile.get("base_hashrate", "—"))),
			]
			_surface_details.text = "TIER  %s    CURRENT HARDWARE  %s    NEXT UPGRADE  %s" % [
				str(profile.get("player_tier", "—")),
				str(profile.get("hardware_id", "—")),
				str((profile.get("next_recommended_upgrade", {}) as Dictionary).get("name", "None available")),
			]
		"POWER":
			readout = "POWER  %s / %s    THROTTLE  %s" % [
				str(profile.get("power_consumed", machine.get("power_consumption", "—"))),
				str(profile.get("power_capacity", machine.get("power_budget", "—"))),
				str(profile.get("power_throttle_multiplier", machine.get("power_throttle", "—"))),
			]
			_surface_details.text = "AVAILABLE HEADROOM  %s    POWER STATE  Server-authoritative" % str(profile.get("power_available", "—"))
		"STORAGE":
			readout = "BALANCE  %s    RESOURCES  %s" % [
				str(economy.get("balance", economy.get("credits", "—"))),
				str((economy.get("resources", []) as Array).size()),
			]
			_surface_details.text = "INVENTORY ITEMS  %s    BALANCE SOURCE  Economy ledger" % str((profile.get("inventory", []) as Array).size())
		"MARKET":
			readout = "CATALOG ITEMS  %s    STOCK AND PRICES  SERVER-OWNED" % str((status.get("market_catalog", []) as Array).size())
			_surface_details.text = "CATALOG  %s items    PURCHASES  Session-bound server intent" % str((status.get("market_catalog", []) as Array).size())
		"NETWORK":
			readout = "BLOCK  #%s    WORK  %s / %s    PROGRESS  %s%%" % [
				str(status.get("active_block_number", "—")),
				str(status.get("active_accumulated_work", "—")),
				str(status.get("active_required_work", "—")),
				str(float(status.get("active_progress_ratio", 0.0)) * 100.0),
			]
			_surface_details.text = "BLOCK HISTORY  %s    EVENTS  %s    POOLS  %s    LEADERBOARD ENTRIES  %s    YOUR RANK  %s" % [
				str((blocks.get("items", []) as Array).size()),
				str((events.get("items", []) as Array).size()),
				str((pools.get("pools", []) as Array).size()),
				str((leaderboard.get("leaderboard", []) as Array).size()),
				str(position.get("hashrate_rank", "—")),
			]
		"RESEARCH":
			readout = "PROGRESSION GATE  SERVER CONFIRMATION REQUIRED"

	_surface_readout.text = readout
