extends RefCounted
class_name GmnStarterMachineSmoke

func run() -> Dictionary:
	var view_model := GameplayShellViewModel.new()
	var mapped := view_model.map_profile({
		"hardware_id": "starter_rusty_home_computer",
		"base_hashrate": 12.0,
		"effective_hashrate": 12.0,
		"power_consumed": 120.0,
		"power_capacity": 120.0,
		"power_throttle_multiplier": 1.0,
		"heat_generated": 40.0,
		"cooling_efficiency_multiplier": 1.0,
		"cooling_capacity": 100.0,
		"player_tier": 1,
		"current_hardware": {"name": "Rusty Home Computer"},
	})
	var failures: Array[String] = []
	if mapped.get("machine_name_text") != "Rusty Home Computer":
		failures.append("machine name did not map from profile")
	if mapped.get("effective_hashrate_text") != "12.0":
		failures.append("effective hashrate did not map from profile")
	if mapped.get("power_text") != "120.0 / 120.0":
		failures.append("power values did not map from profile")
	if mapped.get("cooling_text") != "1.0 / 100.0":
		failures.append("cooling values did not map from profile")
	return {"ok": failures.is_empty(), "failures": failures}
