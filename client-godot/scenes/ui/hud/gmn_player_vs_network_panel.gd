## GMN Player vs Network Panel
## Shows the player's effective hashrate vs the global network hashrate.
## Contribution share is [awaiting server read model] — marked as placeholder
## so client never calculates it locally.

extends Control
class_name GmnPlayerVsNetworkPanel

@export var player_hashrate_label_path: NodePath
@export var global_hashrate_label_path: NodePath
@export var contribution_label_path: NodePath

@onready var _player_hashrate: Label  = get_node_or_null(player_hashrate_label_path)
@onready var _global_hashrate: Label  = get_node_or_null(global_hashrate_label_path)
@onready var _contribution: Label     = get_node_or_null(contribution_label_path)

## Update from server-provided payloads.
## effective_hps: from EffectiveHashrateService (server-authoritative).
## global_hps: from BlockStatus.global_hashrate (server-authoritative).
## contribution_pct: from server read model if available, otherwise null/empty.
func update_from_payloads(effective_hps: float, global_hps: float, contribution_pct) -> void:
	if _player_hashrate:
		_player_hashrate.text = "YOUR HASHRATE\n%s" % _fmt_hps(effective_hps)
	if _global_hashrate:
		_global_hashrate.text = "GLOBAL HASHRATE\n%s" % (_fmt_hps(global_hps) if global_hps > 0.0 else "Server readout pending")
	if _contribution:
		if contribution_pct != null and str(contribution_pct) != "":
			_contribution.text = "SHARE  %.6f%%" % float(contribution_pct)
		else:
			_contribution.text = "SHARE  Server contribution readout pending"

func _fmt_hps(hps: float) -> String:
	if hps >= 1_000_000_000_000.0:
		return "%.2f TH/s" % (hps / 1_000_000_000_000.0)
	if hps >= 1_000_000_000.0:
		return "%.2f GH/s" % (hps / 1_000_000_000.0)
	if hps >= 1_000_000.0:
		return "%.2f MH/s" % (hps / 1_000_000.0)
	if hps >= 1_000.0:
		return "%.2f KH/s" % (hps / 1_000.0)
	return "%.2f H/s" % hps
