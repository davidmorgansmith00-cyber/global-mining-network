extends Control
class_name OnboardingSceneRoot

const GAMEPLAY_SCENE_PATH := "res://scenes/gameplay_shell.tscn"

var api_client: GmnApiClient
var email_input: LineEdit
var password_input: LineEdit
var login_button: Button
var register_button: Button
var status_label: Label
var error_label: Label
var _busy := false

func _ready() -> void:
	_build_ui()
	api_client = GmnApiClient.new()
	api_client.configure("http://127.0.0.1:8000")
	add_child(api_client)

func _build_ui() -> void:
	var background := ColorRect.new()
	background.color = Color("101820")
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(background)

	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(center)

	var panel := PanelContainer.new()
	panel.custom_minimum_size = Vector2(460, 420)
	center.add_child(panel)

	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 14)
	panel.add_child(content)

	var title := Label.new()
	title.text = "GLOBAL MINING NETWORK"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 26)
	content.add_child(title)

	var introduction := Label.new()
	introduction.text = "Join one shared fictional global chain.\nThe server owns progression, rewards, and network reality."
	introduction.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	introduction.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	content.add_child(introduction)

	var divider := HSeparator.new()
	content.add_child(divider)

	email_input = LineEdit.new()
	email_input.placeholder_text = "Email"
	email_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	email_input.text = ""
	content.add_child(email_input)

	password_input = LineEdit.new()
	password_input.placeholder_text = "Password"
	password_input.secret = true
	password_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	content.add_child(password_input)

	var actions := HBoxContainer.new()
	actions.alignment = BoxContainer.ALIGNMENT_CENTER
	actions.add_theme_constant_override("separation", 12)
	content.add_child(actions)

	login_button = Button.new()
	login_button.text = "Log In"
	login_button.custom_minimum_size = Vector2(150, 42)
	login_button.pressed.connect(_on_login_pressed)
	actions.add_child(login_button)

	register_button = Button.new()
	register_button.text = "Create Account"
	register_button.custom_minimum_size = Vector2(150, 42)
	register_button.pressed.connect(_on_register_pressed)
	actions.add_child(register_button)

	status_label = Label.new()
	status_label.text = "Ready to connect"
	status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	content.add_child(status_label)

	error_label = Label.new()
	error_label.visible = false
	error_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	error_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	error_label.add_theme_color_override("font_color", Color("ff9b9b"))
	content.add_child(error_label)

func _on_login_pressed() -> void:
	_submit_auth(false)

func _on_register_pressed() -> void:
	_submit_auth(true)

func _submit_auth(register: bool) -> void:
	if _busy:
		return

	var email := email_input.text.strip_edges()
	var password := password_input.text
	if email == "" or password == "":
		_show_error("Email and password are required.")
		return
	if password.length() < 8:
		_show_error("Password must be at least 8 characters.")
		return

	_busy = true
	_set_controls_enabled(false)
	error_label.visible = false
	status_label.text = "Creating your session..." if register else "Signing in..."

	var auth_response: Dictionary
	if register:
		auth_response = await api_client.register_session(email, password)
	else:
		auth_response = await api_client.login_session(email, password)

	if not auth_response.get("ok", false):
		_busy = false
		_set_controls_enabled(true)
		_show_error(_format_response_error(auth_response, "Authentication failed. Check your details and try again."))
		return

	status_label.text = "Loading your starter operation..."
	var player_id := api_client.session.player_id
	var bootstrap_response := await api_client.fetch_player_bootstrap(player_id)
	if not bootstrap_response.get("ok", false):
		_busy = false
		_set_controls_enabled(true)
		_show_error(_format_response_error(bootstrap_response, "Your session worked, but starter setup could not be loaded."))
		return

	await _open_gameplay_shell()

func _open_gameplay_shell() -> void:
	if not is_inside_tree():
		return
	var tree := get_tree()
	var session_payload := {
		"player_id": api_client.session.player_id,
		"session_id": api_client.session.session_id,
		"access_token": api_client.session.access_token,
		"refresh_token": api_client.session.refresh_token,
	}
	var change_error := tree.change_scene_to_file(GAMEPLAY_SCENE_PATH)
	if change_error != OK:
		_busy = false
		_set_controls_enabled(true)
		_show_error("Gameplay shell could not be opened.")
		return
	var gameplay_root: Node = null
	for _attempt in range(10):
		await tree.process_frame
		gameplay_root = tree.current_scene
		if gameplay_root != null and gameplay_root.has_method("configure_session"):
			break
	if gameplay_root != null and gameplay_root.has_method("configure_session"):
		gameplay_root.configure_session(
			str(session_payload.get("player_id", "")),
			str(session_payload.get("session_id", "")),
			str(session_payload.get("access_token", "")),
			str(session_payload.get("refresh_token", "")),
		)
	else:
		push_error("Gameplay shell was not ready for session handoff")

func _set_controls_enabled(enabled: bool) -> void:
	email_input.editable = enabled
	password_input.editable = enabled
	login_button.disabled = not enabled
	register_button.disabled = not enabled

func _show_error(message: String) -> void:
	error_label.text = message
	error_label.visible = true
	status_label.text = "Unable to continue"

func _format_response_error(response: Dictionary, fallback: String) -> String:
	var payload: Variant = response.get("payload", {})
	if payload is Dictionary:
		var detail := str((payload as Dictionary).get("detail", ""))
		if detail != "":
			return detail
	var error := str(response.get("error", ""))
	return error if error != "" else fallback
