extends RefCounted
class_name GmnUiStateSmoke

func run() -> Dictionary:
	var state := GameplayShellUiState.new()
	var failures: Array[String] = []

	if state.state_code != GameplayShellUiState.LOADING:
		failures.append("initial state must be loading")

	state.set_ready()
	if state.state_code != GameplayShellUiState.READY:
		failures.append("ready transition failed")
	if state.last_updated_unix_seconds <= 0:
		failures.append("ready state must record an update timestamp")

	state.set_stale()
	if state.state_code != GameplayShellUiState.STALE:
		failures.append("stale transition failed")

	state.set_unauthorized()
	if state.state_code != GameplayShellUiState.UNAUTHORIZED:
		failures.append("unauthorized transition failed")

	state.set_maintenance()
	if state.state_code != GameplayShellUiState.MAINTENANCE:
		failures.append("maintenance transition failed")

	state.set_error()
	if state.state_code != GameplayShellUiState.ERROR:
		failures.append("error transition failed")

	return {
		"ok": failures.is_empty(),
		"failures": failures,
	}
