extends Node
class_name GmnApiClient

const AUTH_REGISTER_PATH := "/api/v1/auth/register"
const AUTH_LOGIN_PATH := "/api/v1/auth/login"
const STATUS_PATH := "/api/v1/blockchain/status"
const SNAPSHOT_PATH := "/api/v1/blockchain/network-snapshot"
const REWARDS_PATH_TEMPLATE := "/api/v1/blockchain/players/%s/rewards"
const CHECKPOINT_PATH_TEMPLATE := "/api/v1/blockchain/checkpoints/%s"
const OPERATION_START_INTENT_PATH := "/api/v1/blockchain/operations/intents/start"
const OPERATION_STOP_INTENT_PATH := "/api/v1/blockchain/operations/intents/stop"

var base_url: String = "http://127.0.0.1:8000"
var player_id: String = ""
var session_id: String = ""
var access_token: String = ""
var refresh_token: String = ""
var _http: HTTPRequest

func _ready() -> void:
	_http = HTTPRequest.new()
	add_child(_http)

func configure(url: String) -> void:
	base_url = url.rstrip("/")

func set_session(session: Dictionary) -> void:
	player_id = str(session.get("player_id", ""))
	session_id = str(session.get("session_id", ""))
	access_token = str(session.get("access_token", ""))
	refresh_token = str(session.get("refresh_token", ""))

func build_status_url(recent_limit: int = 10) -> String:
	return "%s%s?recent_limit=%d" % [base_url, STATUS_PATH, recent_limit]

func build_snapshot_url(recent_limit: int = 10) -> String:
	return "%s%s?recent_limit=%d" % [base_url, SNAPSHOT_PATH, recent_limit]

func build_rewards_url(target_player_id: String, recent_limit: int = 20) -> String:
	return "%s%s?recent_limit=%d" % [
		base_url,
		REWARDS_PATH_TEMPLATE % target_player_id,
		recent_limit,
	]

func build_auth_register_url() -> String:
	return "%s%s" % [base_url, AUTH_REGISTER_PATH]

func build_auth_login_url() -> String:
	return "%s%s" % [base_url, AUTH_LOGIN_PATH]

func register_session(email: String, password: String) -> Dictionary:
	var payload := {"email": email, "password": password}
	return await _request_json(HTTPClient.METHOD_POST, build_auth_register_url(), payload)

func login_session(email: String, password: String) -> Dictionary:
	var payload := {"email": email, "password": password}
	return await _request_json(HTTPClient.METHOD_POST, build_auth_login_url(), payload)

func fetch_status(recent_limit: int = 10) -> Dictionary:
	return await _request_json(HTTPClient.METHOD_GET, build_status_url(recent_limit))

func fetch_snapshot(recent_limit: int = 10) -> Dictionary:
	return await _request_json(HTTPClient.METHOD_GET, build_snapshot_url(recent_limit))

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
	return "%s%s?session_id=%s" % [base_url, OPERATION_START_INTENT_PATH, session_id]

func build_operation_stop_intent_url() -> String:
	return "%s%s?session_id=%s" % [base_url, OPERATION_STOP_INTENT_PATH, session_id]

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

func _request_json(method: HTTPClient.Method, url: String, payload: Dictionary = {}) -> Dictionary:
	var body := ""
	var headers: PackedStringArray = []
	if method != HTTPClient.METHOD_GET:
		headers.append("Content-Type: application/json")
		body = JSON.stringify(payload)

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
