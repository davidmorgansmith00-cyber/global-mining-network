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

var _controller: GameplayShellController

func _ready() -> void:
	_controller = get_node_or_null(controller_path)
	_nav_bar.surface_selected.connect(_on_surface_selected)

## Call after GameplayShellController.refresh_authoritative_views() completes.
func refresh_from_controller() -> void:
	if _controller == null:
		return

	var status   := _controller.latest_status_payload
	var profile  := _controller.latest_profile_payload
	var snapshot := _controller.latest_snapshot_payload

	# Refresh global block header
	_global_block_header.update_from_block_status(status)

	# Refresh player operation panel — machine state from snapshot or status
	var machine_state: Dictionary = snapshot.get("machine_state", {})
	_player_op.update_from_payloads(profile, machine_state)

	# Refresh player vs network
	var eff_hps := float(machine_state.get("effective_hashrate", 0.0))
	var global_hps := float(status.get("global_hashrate", 0.0))
	var contribution = machine_state.get("contribution_percent", null)
	_vs_network.update_from_payloads(eff_hps, global_hps, contribution)

	# Refresh resource strip
	var economy := profile.get("economy", profile)
	_resource_strip.update_from_payload(economy)

func _on_surface_selected(surface_id: String) -> void:
	# Surface switching is handled at the gameplay shell level in V1/V2.
	# This signal is available for the parent scene to respond to.
	pass
