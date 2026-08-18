## ReportPanel.gd
## In-game support report panel.
## Accessible from any menu via the report button.
## Submits a support ticket to the server.

extends Control

const _CATEGORIES = ["bug", "player_behavior", "content", "exploit"]

@onready var _category_option: OptionButton = $MarginContainer/VBox/CategoryOption
@onready var _title_input: LineEdit = $MarginContainer/VBox/TitleInput
@onready var _description_input: TextEdit = $MarginContainer/VBox/DescriptionInput
@onready var _screenshot_button: Button = $MarginContainer/VBox/ScreenshotButton
@onready var _submit_button: Button = $MarginContainer/VBox/SubmitButton
@onready var _result_label: Label = $MarginContainer/VBox/ResultLabel

var _screenshot_b64: String = ""
var _api_client  # GmnApiClient — injected by parent

signal report_submitted(ticket_id: String)


func _ready() -> void:
	_result_label.text = ""
	_category_option.clear()
	for cat in _CATEGORIES:
		_category_option.add_item(cat)
	_screenshot_button.pressed.connect(_capture_screenshot)
	_submit_button.pressed.connect(_on_submit_pressed)


func set_api_client(client) -> void:
	_api_client = client


func _capture_screenshot() -> void:
	# Capture viewport image and encode as base64
	var image: Image = get_viewport().get_texture().get_image()
	_screenshot_b64 = Marshalls.raw_to_base64(image.save_png_to_buffer())
	_screenshot_button.text = "Screenshot captured ✓"


func _on_submit_pressed() -> void:
	var title: String = _title_input.text.strip_edges()
	var description: String = _description_input.text.strip_edges()
	if title.is_empty() or description.is_empty():
		_result_label.text = "Please fill in title and description."
		return

	_submit_button.disabled = true
	_result_label.text = "Submitting…"

	var category: String = _CATEGORIES[_category_option.selected]
	var payload := {
		"player_id": _get_player_id(),
		"title": title,
		"description": description,
		"category": category,
		"screenshot_b64": _screenshot_b64 if not _screenshot_b64.is_empty() else null,
		"player_state": _collect_player_state(),
		"environment_info": _collect_environment_info(),
	}

	if _api_client != null:
		_api_client.post("/api/v1/support/report", payload, _on_report_response)
	else:
		_result_label.text = "Error: API client not configured."
		_submit_button.disabled = false


func _on_report_response(response: Dictionary) -> void:
	_submit_button.disabled = false
	if response.has("ticket_id"):
		var ticket_id: String = response["ticket_id"]
		_result_label.text = "Submitted! Ticket ID: %s" % ticket_id
		report_submitted.emit(ticket_id)
		_title_input.clear()
		_description_input.clear()
		_screenshot_b64 = ""
		_screenshot_button.text = "Capture Screenshot"
	else:
		_result_label.text = "Submission failed. Please try again."


func _get_player_id() -> String:
	# Retrieve player ID from session singleton (set during login)
	if Engine.has_singleton("GmnSession"):
		return Engine.get_singleton("GmnSession").player_id
	return "unknown"


func _collect_player_state() -> Dictionary:
	# Collect current player state for evidence purposes
	return {
		"source": "client",
		"timestamp": Time.get_datetime_string_from_system(true),
	}


func _collect_environment_info() -> Dictionary:
	return {
		"os": OS.get_name(),
		"game_version": ProjectSettings.get_setting("application/config/version", "unknown"),
		"display_size": "%dx%d" % [DisplayServer.screen_get_size().x, DisplayServer.screen_get_size().y],
	}
