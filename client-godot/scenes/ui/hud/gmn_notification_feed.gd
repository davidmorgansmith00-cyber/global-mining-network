## GMN Notification Feed
## Priority-queued notification display.
## Priorities: critical (3) > operational (2) > informational (1).
## All event data originates from the server event stream — client never
## emits game-state notifications locally.

extends Control
class_name GmnNotificationFeed

const MAX_VISIBLE := 4
const AUTO_DISMISS_SECONDS := 5.0

enum Priority { INFORMATIONAL = 1, OPERATIONAL = 2, CRITICAL = 3 }

class Notification:
	var text: String
	var priority: int
	var age_seconds: float = 0.0
	func _init(t: String, p: int) -> void:
		text = t
		priority = p

var _queue: Array[Notification] = []
var _labels: Array[Label] = []

@export var container_path: NodePath
@onready var _container: Control = get_node_or_null(container_path)

func _ready() -> void:
	for i in range(MAX_VISIBLE):
		var lbl := Label.new()
		lbl.visible = false
		lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		lbl.custom_minimum_size = Vector2(304.0, 24.0)
		lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		lbl.focus_mode = Control.FOCUS_ALL
		if _container:
			_container.add_child(lbl)
		_labels.append(lbl)

func _process(delta: float) -> void:
	for n in _queue:
		n.age_seconds += delta
	_queue = _queue.filter(func(n): return n.age_seconds < AUTO_DISMISS_SECONDS)
	_queue.sort_custom(func(a, b): return a.priority > b.priority)
	_refresh_display()

## Push a notification from a server event. priority = 1/2/3.
func push(text: String, priority: int = Priority.INFORMATIONAL) -> void:
	var n := Notification.new(text, priority)
	_queue.append(n)

## Convenience helpers
func push_block_reward(amount: float) -> void:
	push("⬡ Block reward  +%.4f Ƀ" % amount, Priority.OPERATIONAL)

func push_purchase_complete(item_id: String) -> void:
	push("✓ Purchased  %s" % item_id, Priority.INFORMATIONAL)

func push_upgrade_started(item_id: String) -> void:
	push("⚙ Upgrade started  %s" % item_id, Priority.INFORMATIONAL)

func push_upgrade_complete(item_id: String) -> void:
	push("✓ Upgrade complete  %s" % item_id, Priority.OPERATIONAL)

func push_critical(text: String) -> void:
	push(text, Priority.CRITICAL)

func _refresh_display() -> void:
	for i in range(MAX_VISIBLE):
		if i < _queue.size():
			var n: Notification = _queue[i]
			_labels[i].text = n.text
			_labels[i].visible = true
			var col: Color = _priority_colour(n.priority)
			_labels[i].add_theme_color_override("font_color", col)
		else:
			_labels[i].visible = false

func _priority_colour(priority: int) -> Color:
	match priority:
		Priority.CRITICAL:
			return GmnUiTokens.ACCENT_DANGER
		Priority.OPERATIONAL:
			return GmnUiTokens.ACCENT_SUCCESS
		_:
			return GmnUiTokens.TEXT_SECONDARY

func get_primary_focus_target() -> Control:
	if not _labels.is_empty():
		return _labels[0]
	return null
