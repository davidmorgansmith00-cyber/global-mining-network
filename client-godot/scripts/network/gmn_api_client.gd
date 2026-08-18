extends Node
class_name GmnApiClient

const AUTH_REGISTER_PATH := "/api/v1/auth/register"
const AUTH_LOGIN_PATH := "/api/v1/auth/login"
const AUTH_REFRESH_PATH := "/api/v1/auth/refresh"
const AUTH_LOGOUT_PATH := "/api/v1/auth/logout"
const STATUS_PATH := "/api/v1/blockchain/status"
const SNAPSHOT_PATH := "/api/v1/blockchain/network-snapshot"
const PLAYER_PROFILE_PATH := "/api/v1/players/profile"
const REWARDS_PATH_TEMPLATE := "/api/v1/blockchain/players/%s/rewards"
const CHECKPOINT_PATH_TEMPLATE := "/api/v1/blockchain/checkpoints/%s"
const OPERATION_START_INTENT_PATH := "/api/v1/blockchain/operations/intents/start"
const OPERATION_STOP_INTENT_PATH := "/api/v1/blockchain/operations/intents/stop"

var base_url: String = "http://127.0.0.1:8000"
var session: GmnSession = GmnSession.new()
var _http: HTTPRequest

func _ready() -> void:
	_http = HTTPRequest.new()
	add_child(_http)

func configure(url: String) -> void:
	base_url = url.rstrip("/")

## BOOTSTRAP SESSION: Register a new player
func register_session(email: String, password: String) -> Dictionary:
	var payload := {"email": email, "password": password}
	var response = await _request_json(HTTPClient.METHOD_POST, build_auth_register_url(), payload)
	
	# On success, populate session from response
	if response.get("ok", false) and response.get("payload"):
		var payload_data = response.get("payload")
		session.set_from_response({
			"player_id": payload_data.get("player_id", ""),
			"session_id": payload_data.get("session_id", ""),
			"access_token": payload_data.get("access_token", ""),
			"refresh_token": payload_data.get("refresh_token", ""),
			"expires_in": payload_data.get("expires_in", 3600)
		})
	
	return response

## BOOTSTRAP SESSION: Login existing player
func login_session(email: String, password: String) -> Dictionary:
	var payload := {"email": email, "password": password}
	var response = await _request_json(HTTPClient.METHOD_POST, build_auth_login_url(), payload)
	
	# On success, populate session from response
	if response.get("ok", false) and response.get("payload"):
		var payload_data = response.get("payload")
		session.set_from_response({
			"player_id": payload_data.get("player_id", ""),
			"session_id": payload_data.get("session_id", ""),
			"access_token": payload_data.get("access_token", ""),
			"refresh_token": payload_data.get("refresh_token", ""),
			"expires_in": payload_data.get("expires_in", 3600)
		})
	
	return response

## BOOTSTRAP SESSION: Refresh expired token
func refresh_access_token() -> Dictionary:
	if session.refresh_token == "":
		return {
			"ok": false,
			"error": "No refresh token available",
			"status_code": 401
		}
	
	var payload := {"refresh_token": session.refresh_token}
	var response = await _request_json(HTTPClient.METHOD_POST, build_auth_refresh_url(), payload)
	
	# On success, update session tokens
	if response.get("ok", false) and response.get("payload"):
		var payload_data = response.get("payload")
		session.set_from_response({
			"player_id": session.player_id,  # Keep existing player_id
			"session_id": payload_data.get("session_id", session.session_id),
			"access_token": payload_data.get("access_token", ""),
			"refresh_token": payload_data.get("refresh_token", ""),
			"expires_in": payload_data.get("expires_in", 3600)
		})
	
	return response

## BOOTSTRAP SESSION: Logout and revoke token
func logout_session() -> Dictionary:
	if session.player_id == "":
		return {
			"ok": false,
			"error": "No active session",
			"status_code": 401
		}
	
	var response = await _request_json(HTTPClient.METHOD_POST, build_auth_logout_url(), {})
	
	# On success, clear session
	if response.get("ok", false):
		session.clear()
	
	return response

func build_auth_register_url() -> String:
	return "%s%s" % [base_url, AUTH_REGISTER_PATH]

func build_auth_login_url() -> String:
	return "%s%s" % [base_url, AUTH_LOGIN_PATH]

func build_auth_refresh_url() -> String:
	return "%s%s" % [base_url, AUTH_REFRESH_PATH]

func build_auth_logout_url() -> String:
	return "%s%s" % [base_url, AUTH_LOGOUT_PATH]

func build_status_url(recent_limit: int = 10) -> String:
	return "%s%s?recent_limit=%d" % [base_url, STATUS_PATH, recent_limit]

func build_snapshot_url(recent_limit: int = 10) -> String:
	return "%s%s?recent_limit=%d" % [base_url, SNAPSHOT_PATH, recent_limit]

func build_player_profile_url(target_player_id: String) -> String:
	return "%s%s?player_id=%s" % [base_url, PLAYER_PROFILE_PATH, target_player_id]

func build_rewards_url(target_player_id: String, recent_limit: int = 20) -> String:
	return "%s%s?recent_limit=%d" % [
		base_url,
		REWARDS_PATH_TEMPLATE % target_player_id,
		recent_limit,
	]

func fetch_status(recent_limit: int = 10) -> Dictionary:
	return await _request_json(HTTPClient.METHOD_GET, build_status_url(recent_limit))

func fetch_snapshot(recent_limit: int = 10) -> Dictionary:
	return await _request_json(HTTPClient.METHOD_GET, build_snapshot_url(recent_limit))

func fetch_player_profile(target_player_id: String) -> Dictionary:
	return await _request_json(HTTPClient.METHOD_GET, build_player_profile_url(target_player_id))

func fetch_rewards(target_player_id: String, recent_limit: int = 20) -> Dictionary:
	return await _request_json(HTTPClient.METHOD_GET, build_rewards_url(target_player_id, recent_limit))

func fetch_checkpoint(channel: String, target_player_id: String, target_session_id: String) -> Dictionary:
	var path := CHECKPOINT_PATH_TEMPLATE % channel
	var url := "%s%s?player_id=%s&session_id=%s" % [base_url, path, target_player_id, target_session_id]
	return await _request_json(HTTPClient.METHOD_GET, url)

func upsert_checkpoint(channel: String, target_player_id: String, target_session_id: String, reconnect_cursor: int) -> Dictionary:
	var path := CHECKPOINT_PATH_TEMPLATE % channel
	var url := "%s%s?player_id=%s&session_id=%s" % [base_url, path, target_player_id, target_session_id]
	var payload := {"reconnect_cursor": reconnect_cursor}
	return await _request_json(HTTPClient.METHOD_PUT, url, payload)

func build_operation_start_intent_url() -> String:
	return "%s%s?session_id=%s" % [base_url, OPERATION_START_INTENT_PATH, session.session_id]

func build_operation_stop_intent_url() -> String:
	return "%s%s?session_id=%s" % [base_url, OPERATION_STOP_INTENT_PATH, session.session_id]

func build_operation_start_intent_payload(operation_id: String, base_hashrate_hps: float) -> Dictionary:
	return {
		"operation_id": operation_id,
		"base_hashrate_hps": base_hashrate_hps,
	}

func build_operation_stop_intent_payload(operation_id: String) -> Dictionary:
	return {
		"operation_id": operation_id,
	}

func send_operation_start_intent(operation_id: String, base_hashrate_hps: float) -> Dictionary:
	var payload := build_operation_start_intent_payload(operation_id, base_hashrate_hps)
	var url := build_operation_start_intent_url()
	return await _request_json(
		HTTPClient.METHOD_POST,
		url,
		payload,
	)

func send_operation_stop_intent(operation_id: String) -> Dictionary:
	var payload := build_operation_stop_intent_payload(operation_id)
	var url := build_operation_stop_intent_url()
	return await _request_json(
		HTTPClient.METHOD_POST,
		url,
		payload,
	)

func set_session(payload: Dictionary) -> void:
	session.set_from_response(payload)

## Get current session (read-only)
func get_session() -> GmnSession:
	return session

## Check if session is valid
func is_authenticated() -> bool:
	return session.is_valid()

func _request_json(method: HTTPClient.Method, url: String, payload: Dictionary = {}) -> Dictionary:
	var body := ""
	var headers: PackedStringArray = []
	
	if method != HTTPClient.METHOD_GET:
		headers.append("Content-Type: application/json")
		body = JSON.stringify(payload)
	
	# Add authorization header if session has access token
	if session.access_token != "":
		headers.append("Authorization: Bearer %s" % session.access_token)
	
	var error := _http.request(url, headers, method, body)
	if error != OK:
		return {
			"ok": false,
			"status_code": 0,
			"error": "request_start_failed",
			"error_code": error,
		}

	var completed: Array = await _http.request_completed
	var request_result: int = completed[0]
	var response_code: int = completed[1]
	var response_body: PackedByteArray = completed[3]
	var raw_text := response_body.get_string_from_utf8()
	var parsed = JSON.parse_string(raw_text)
	var parsed_payload: Variant = parsed if parsed != null else raw_text

	return {
		"ok": request_result == HTTPRequest.RESULT_SUCCESS and response_code >= 200 and response_code < 300,
		"status_code": response_code,
		"request_result": request_result,
		"payload": parsed_payload,
	}
