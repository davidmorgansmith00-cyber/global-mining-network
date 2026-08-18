## GMN Session Bootstrap
## Stores authoritative player session data (runtime only, non-persistent)
## Server provides all truth; client displays only

class_name GmnSession
extends RefCounted

## Session state (runtime only, never persisted to disk)
var player_id: String = ""
var session_id: String = ""
var access_token: String = ""
var refresh_token: String = ""
var token_expires_at: float = 0.0

## Is this session currently valid?
func is_valid() -> bool:
	return player_id != "" and access_token != "" and (Time.get_ticks_msec() / 1000.0) < token_expires_at

## Refresh token if expired
func should_refresh() -> bool:
	var now = Time.get_ticks_msec() / 1000.0
	return token_expires_at > 0 and now > (token_expires_at - 300)  # Refresh 5 min before expiry

## Clear session (logout or expired)
func clear() -> void:
	player_id = ""
	session_id = ""
	access_token = ""
	refresh_token = ""
	token_expires_at = 0.0

## Set from auth response
func set_from_response(response: Dictionary) -> void:
	player_id = response.get("player_id", "")
	session_id = response.get("session_id", "")
	access_token = response.get("access_token", "")
	refresh_token = response.get("refresh_token", "")
	var expires_in = response.get("expires_in", 3600)
	token_expires_at = Time.get_ticks_msec() / 1000.0 + expires_in
