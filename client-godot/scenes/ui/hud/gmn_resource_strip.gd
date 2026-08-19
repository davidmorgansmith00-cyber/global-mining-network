## GMN Resource Strip
## Persistent credits + key resource display.
## Positioned below the Global Block Header.
## All values are server-authoritative from economy read models.

extends Control
class_name GmnResourceStrip

@export var credits_label_path: NodePath
@export var resource_a_label_path: NodePath
@export var resource_b_label_path: NodePath

@onready var _credits: Label     = get_node_or_null(credits_label_path)
@onready var _resource_a: Label  = get_node_or_null(resource_a_label_path)
@onready var _resource_b: Label  = get_node_or_null(resource_b_label_path)

## Update from server-provided balance/inventory payload.
func update_from_payload(payload: Dictionary) -> void:
	var balance: Variant = payload.get("reward_balance", payload.get("balance", payload.get("credits", 0.0)))
	if _credits:
		_credits.text = "CREDITS AVAILABLE: %s" % _fmt_balance(float(balance))
	var resources: Array = payload.get("resources", [])
	if resources.size() > 0 and _resource_a:
		var r: Dictionary = resources[0] as Dictionary
		_resource_a.text = "%s: %s" % [str(r.get("name", "RESOURCE")).to_upper(), str(r.get("quantity", 0))]
	if resources.size() > 1 and _resource_b:
		var r: Dictionary = resources[1] as Dictionary
		_resource_b.text = "%s: %s" % [str(r.get("name", "RESOURCE")).to_upper(), str(r.get("quantity", 0))]

func _fmt_balance(v: float) -> String:
	if v >= 1_000_000.0:
		return "%.2fM" % (v / 1_000_000.0)
	if v >= 1_000.0:
		return "%.1fK" % (v / 1_000.0)
	return "%.0f" % v
