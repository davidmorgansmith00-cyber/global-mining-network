extends RefCounted
class_name GmnOperationIntentContractSmoke

# Validates client request-shape rules for session-bound operation intents.
func run() -> Dictionary:
	var api_client := GmnApiClient.new()
	api_client.configure("http://127.0.0.1:8000")
	api_client.set_session(
		{
			"player_id": "player-smoke-a",
			"session_id": "session-smoke-a",
			"access_token": "access-smoke",
			"refresh_token": "refresh-smoke",
		}
	)

	var start_payload := api_client.build_operation_start_intent_payload("op_smoke_1", 42.5)
	var stop_payload := api_client.build_operation_stop_intent_payload("op_smoke_1")
	var start_url := api_client.build_operation_start_intent_url()
	var stop_url := api_client.build_operation_stop_intent_url()

	var failures: Array[String] = []
	if not start_payload.has("operation_id"):
		failures.append("start payload missing operation_id")
	if not start_payload.has("base_hashrate_hps"):
		failures.append("start payload missing base_hashrate_hps")
	if start_payload.has("player_id"):
		failures.append("start payload must not include player_id")

	if not stop_payload.has("operation_id"):
		failures.append("stop payload missing operation_id")
	if stop_payload.has("player_id"):
		failures.append("stop payload must not include player_id")

	if start_url.find("session_id=session-smoke-a") == -1:
		failures.append("start URL missing session_id query parameter")
	if stop_url.find("session_id=session-smoke-a") == -1:
		failures.append("stop URL missing session_id query parameter")

	return {
		"ok": failures.is_empty(),
		"failures": failures,
	}
