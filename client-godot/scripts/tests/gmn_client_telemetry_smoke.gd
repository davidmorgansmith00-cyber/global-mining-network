extends RefCounted
class_name GmnClientTelemetrySmoke

func run() -> Dictionary:
	var telemetry := GmnClientTelemetry.new()
	telemetry.record("login_succeeded", {"mode": "login", "player_id": "private", "access_token": "private"})
	telemetry.record("not_allowed", {"value": "ignored"})
	var events := telemetry.drain()
	var failures: Array[String] = []
	if events.size() != 1:
		failures.append("telemetry allowlist failed")
	if events[0].get("properties", {}).has("player_id"):
		failures.append("private player identity was retained")
	if events[0].get("properties", {}).has("access_token"):
		failures.append("access token was retained")
	if telemetry.size() != 0:
		failures.append("drain did not clear events")
	return {"ok": failures.is_empty(), "failures": failures}
