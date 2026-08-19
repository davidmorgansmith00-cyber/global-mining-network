## GMN Player Operation Panel
## Compact persistent panel showing the player's current machine and operating state.
## All values are server-authoritative. Client never derives throttle, heat,
## cooling multiplier, or effective hashrate locally.

extends Control
class_name GmnPlayerOperationPanel

## Authoritative machine state enum (matches server enum)
enum MachineStatus { MINING, IDLE, THROTTLED, OFFLINE, UPGRADING, UNKNOWN }

@export var machine_name_label_path: NodePath
@export var status_badge_label_path: NodePath
@export var hashrate_label_path: NodePath
@export var effective_hashrate_label_path: NodePath
@export var power_label_path: NodePath
@export var throttle_label_path: NodePath
@export var heat_label_path: NodePath
@export var cooling_label_path: NodePath
@export var upgrade_label_path: NodePath

@onready var _machine_name: Label        = get_node_or_null(machine_name_label_path)
@onready var _status_badge: Label        = get_node_or_null(status_badge_label_path)
@onready var _hashrate: Label            = get_node_or_null(hashrate_label_path)
@onready var _effective_hashrate: Label  = get_node_or_null(effective_hashrate_label_path)
@onready var _power: Label               = get_node_or_null(power_label_path)
@onready var _throttle: Label            = get_node_or_null(throttle_label_path)
@onready var _heat: Label                = get_node_or_null(heat_label_path)
@onready var _cooling: Label             = get_node_or_null(cooling_label_path)
@onready var _upgrade: Label             = get_node_or_null(upgrade_label_path)

## Update panel from server-provided profile and machine state payloads.
## Source: PlayerProfile (hardware, base_hashrate), EffectiveHashrateService,
##         PowerState, CoolingState, OperationIntent, UpgradeState
func update_from_payloads(profile: Dictionary, machine: Dictionary) -> void:
	var hw: Dictionary = profile.get("hardware", profile) as Dictionary
	var name := str(hw.get("name", hw.get("hardware_name", "—")))
	var tier := str(hw.get("tier", ""))
	var base_hps   := float(hw.get("base_hashrate", 0.0))
	var eff_hps    := float(machine.get("effective_hashrate", 0.0))
	var power_cur  := float(machine.get("power_consumption", machine.get("power", 0.0)))
	var power_cap  := float(machine.get("power_budget", machine.get("power_limit", 0.0)))
	var throttle   := float(machine.get("power_throttle", machine.get("throttle_multiplier", 1.0)))
	var heat       := float(machine.get("heat", 0.0))
	var cooling_eff := float(machine.get("cooling_efficiency", 1.0))
	var op_status  := str(machine.get("operation_status", machine.get("status", "idle")))
	var upgrade: Dictionary = machine.get("upgrade_state", {}) as Dictionary

	if _machine_name:
		var display_name := name
		if tier != "":
			display_name = "%s  [%s]" % [name, tier.to_upper()]
		_machine_name.text = display_name
	if _hashrate:
		_hashrate.text = "BASE  %s" % _fmt_hps(base_hps)
	if _effective_hashrate:
		_effective_hashrate.text = "EFFECTIVE  %s" % _fmt_hps(eff_hps)
	if _power:
		if power_cap > 0.0:
			_power.text = "POWER  %.0f / %.0f W" % [power_cur, power_cap]
		else:
			_power.text = "POWER  %.0f W" % power_cur
	if _throttle:
		_throttle.text = "THROTTLE  %.0f%%" % (throttle * 100.0)
	if _heat:
		_heat.text = "HEAT  %.1f°C" % heat
	if _cooling:
		_cooling.text = "COOLING  %.0f%%" % (cooling_eff * 100.0)
	if _upgrade:
		var upgrade_active: bool = upgrade.get("active", false)
		_upgrade.text = "UPGRADE IN PROGRESS" if upgrade_active else ""
		_upgrade.visible = upgrade_active

	_apply_status_badge(op_status, throttle, heat)

## Apply status badge text and colour, using warning hierarchy: colour + text (not colour alone).
func _apply_status_badge(op_status: String, throttle: float, heat: float) -> void:
	if _status_badge == null:
		return
	var status := op_status.to_upper()
	var colour: Color = GmnUiTokens.TEXT_SECONDARY

	match status:
		"MINING", "ACTIVE", "RUNNING":
			status = "● MINING"
			colour = GmnUiTokens.ACCENT_SUCCESS
		"UPGRADING":
			status = "⚙ UPGRADING"
			colour = GmnUiTokens.ACCENT_PRIMARY
		"THROTTLED":
			status = "⚠ THROTTLED"
			colour = GmnUiTokens.ACCENT_WARNING
		"OFFLINE", "DISCONNECTED":
			status = "✕ OFFLINE"
			colour = GmnUiTokens.ACCENT_DANGER
		"IDLE", "STOPPED":
			status = "◌ IDLE"
			colour = GmnUiTokens.TEXT_SECONDARY
		_:
			status = "? %s" % status

	# Warning overrides from operational state (colour + symbol, not colour alone)
	if throttle < 0.8 and status.find("OFFLINE") == -1:
		status = "⚠ THROTTLED"
		colour = GmnUiTokens.ACCENT_WARNING
	if heat >= 85.0:
		status = "🔥 OVERHEAT"
		colour = GmnUiTokens.ACCENT_DANGER

	_status_badge.text = status
	_status_badge.add_theme_color_override("font_color", colour)

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
