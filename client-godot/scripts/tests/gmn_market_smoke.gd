extends RefCounted
class_name GmnMarketSmoke

func run() -> Dictionary:
	var view_model := GameplayShellViewModel.new()
	var mapped := view_model.map_market({
		"market_catalog": [
			{"item_id": "starter_gpu_rig_mk1", "price": "250.000000"},
			{"item_id": "upgraded_cooler_v2", "price": "500.000000"},
		]
	})
	var api_client := GmnApiClient.new()
	api_client.configure("http://127.0.0.1:8000")
	api_client.set_session({"session_id": "session-market-smoke"})
	var failures: Array[String] = []
	if mapped.get("item_count_text") != "2":
		failures.append("market item count did not map")
	if str(mapped.get("items_text", "")).find("starter_gpu_rig_mk1") == -1:
		failures.append("market item ID did not map")
	if api_client.build_market_purchase_url().find("session_id=session-market-smoke") == -1:
		failures.append("purchase URL missing session binding")
	return {"ok": failures.is_empty(), "failures": failures}
