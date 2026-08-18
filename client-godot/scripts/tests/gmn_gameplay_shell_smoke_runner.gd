extends Node
class_name GmnGameplayShellSmokeRunner

func run_all() -> Dictionary:
	var suites := {
		"contracts": GmnContractValidationSmoke.new().run(),
		"operation_intents": GmnOperationIntentContractSmoke.new().run(),
		"reconnect": GmnReconnectSmoke.new().run(),
		"ui_state": GmnUiStateSmoke.new().run(),
		"onboarding": GmnOnboardingSmoke.new().run(),
		"starter_machine": GmnStarterMachineSmoke.new().run(),
		"market": GmnMarketSmoke.new().run(),
	}
	var failures: Array[String] = []
	for suite_name in suites.keys():
		var result: Dictionary = suites[suite_name]
		if not result.get("ok", false):
			for detail in result.get("failures", []):
				failures.append("%s: %s" % [suite_name, str(detail)])

	return {
		"ok": failures.is_empty(),
		"failures": failures,
		"suites": suites,
	}
