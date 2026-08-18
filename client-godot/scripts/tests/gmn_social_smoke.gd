extends RefCounted
class_name GmnSocialSmoke

func run() -> Dictionary:
	var api_client := GmnApiClient.new()
	api_client.configure("http://127.0.0.1:8000")
	var view_model := GameplayShellViewModel.new()
	var mapped := view_model.map_social(
		{"pools": [{"pool_id": "pool-1"}]},
		{"leaderboard": [{"rank": 1}]},
		{"hashrate_rank": 1},
	)
	var failures: Array[String] = []
	if mapped.get("pools_text") != "Pools available: 1":
		failures.append("pool count did not map")
	if mapped.get("leaderboard_text") != "Top hashrate entries: 1":
		failures.append("leaderboard count did not map")
	if mapped.get("position_text") != "Your hashrate rank: 1":
		failures.append("player rank did not map")
	return {"ok": failures.is_empty(), "failures": failures}
