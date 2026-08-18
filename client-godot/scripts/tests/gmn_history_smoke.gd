extends RefCounted
class_name GmnHistorySmoke

func run() -> Dictionary:
	var api_client := GmnApiClient.new()
	api_client.configure("http://127.0.0.1:8000")
	var view_model := GameplayShellViewModel.new()
	var mapped := view_model.map_history(
		{"items": [{"block_number": 1}]},
		{"items": [{"block_number": 1, "reward_amount": "0"}]},
		{"items": [{"event_id": "event-1"}]},
	)
	var failures: Array[String] = []
	if api_client.build_explorer_blocks_url().find("/api/v1/explorer/blocks") == -1:
		failures.append("block explorer URL is incorrect")
	if api_client.build_player_history_url("player-history-smoke").find("player-history-smoke") == -1:
		failures.append("player history URL is incorrect")
	if mapped.get("blocks_text") != "Blocks: 1":
		failures.append("block count did not map")
	if mapped.get("player_history_text") != "Your records: 1":
		failures.append("player history count did not map")
	if mapped.get("events_text") != "Active events: 1":
		failures.append("event count did not map")
	return {"ok": failures.is_empty(), "failures": failures}
