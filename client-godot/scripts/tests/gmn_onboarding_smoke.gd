extends RefCounted
class_name GmnOnboardingSmoke

func run() -> Dictionary:
	var api_client := GmnApiClient.new()
	api_client.configure("http://127.0.0.1:8000")
	var failures: Array[String] = []

	if api_client.build_auth_login_url() != "http://127.0.0.1:8000/api/v1/auth/login":
		failures.append("login URL is incorrect")
	if api_client.build_auth_register_url() != "http://127.0.0.1:8000/api/v1/auth/register":
		failures.append("register URL is incorrect")
	if api_client.build_player_bootstrap_url("player-smoke") != "http://127.0.0.1:8000/api/v1/player/bootstrap?player_id=player-smoke":
		failures.append("bootstrap URL is incorrect")

	api_client.set_session({
		"player_id": "player-smoke",
		"session_id": "session-smoke",
		"access_token": "access-smoke",
		"refresh_token": "refresh-smoke",
	})
	if api_client.session.session_id != "session-smoke":
		failures.append("session ID was not retained")

	return {
		"ok": failures.is_empty(),
		"failures": failures,
	}
