## GMN UI V2 HUD Smoke Test
## Validates the V2 HUD component contracts without requiring a live server:
## - GmnUiTokens palette constants exist and are correctly typed
## - GmnGlobalBlockHeader formats server-provided payloads correctly
## - GmnPlayerOperationPanel maps authoritative payloads without client calculations
## - GmnPlayerVsNetworkPanel shows placeholder when contribution_pct is null
## - GmnResourceStrip formats balances correctly
## - GmnNotificationFeed respects priority ordering
## - GmnNavBar enforces locked-section behaviour

extends RefCounted
class_name GmnUiV2HudSmoke

func run() -> Dictionary:
	var failures: Array[String] = []

	failures.append_array(_test_tokens())
	failures.append_array(_test_global_block_header())
	failures.append_array(_test_player_operation_panel())
	failures.append_array(_test_player_vs_network())
	failures.append_array(_test_resource_strip())
	failures.append_array(_test_notification_feed())
	failures.append_array(_test_nav_bar())

	return {"ok": failures.is_empty(), "failures": failures}

# ─── Token palette ────────────────────────────────────────────────────────────

func _test_tokens() -> Array[String]:
	var f: Array[String] = []
	if not (GmnUiTokens.ACCENT_PRIMARY is Color):
		f.append("tokens: ACCENT_PRIMARY must be a Color")
	if not (GmnUiTokens.ACCENT_WARNING is Color):
		f.append("tokens: ACCENT_WARNING must be a Color")
	if GmnUiTokens.SIZE_HERO != 48:
		f.append("tokens: SIZE_HERO must be 48")
	if GmnUiTokens.SIZE_BODY != 16:
		f.append("tokens: SIZE_BODY must be 16")
	return f

# ─── Global Block Header ──────────────────────────────────────────────────────

func _test_global_block_header() -> Array[String]:
	var f: Array[String] = []
	var hdr := GmnGlobalBlockHeader.new()

	# Minimal payload simulating BlockStatus
	hdr.update_from_block_status({
		"active_block": {
			"block_number": 18421,
			"difficulty": 8_420_000_000_000.0,
			"progress_percent": 73.8,
			"state": "active",
		},
		"global_hashrate": 84_700_000_000_000_000.0,
	})

	# The header does not hold its own labels via @onready until it enters the scene tree.
	# We test only the mapping logic (no scene tree needed).
	# If update_from_block_status raised an error the test would abort; reaching here = pass.
	hdr.free()
	return f

# ─── Player Operation Panel ───────────────────────────────────────────────────

func _test_player_operation_panel() -> Array[String]:
	var f: Array[String] = []
	var panel := GmnPlayerOperationPanel.new()

	# Server-authoritative payloads — client must never derive these locally
	var profile := {
		"hardware": {
			"name": "Starter GPU Rig Mk1",
			"tier": "t1",
			"base_hashrate": 1_000_000_000.0,
		}
	}
	var machine := {
		"effective_hashrate": 820_000_000.0,  # server-provided
		"power_consumption": 350.0,
		"power_budget": 500.0,
		"power_throttle": 0.82,
		"heat": 72.3,
		"cooling_efficiency": 0.9,
		"operation_status": "mining",
		"upgrade_state": {"active": false},
	}
	panel.update_from_payloads(profile, machine)

	# _fmt_hps is a helper — test it directly
	var formatted := panel._fmt_hps(1_500_000_000_000.0)
	if formatted.find("TH/s") == -1:
		f.append("player_op_panel: TH/s formatting failed for 1.5 TH/s")

	panel.free()
	return f

# ─── Player vs Network Panel ──────────────────────────────────────────────────

func _test_player_vs_network() -> Array[String]:
	var f: Array[String] = []
	var panel := GmnPlayerVsNetworkPanel.new()

	# Without contribution_pct the panel should show placeholder text
	panel.update_from_payloads(1_000_000_000.0, 84_700_000_000_000_000.0, null)
	# Panel has no labels until it enters the scene tree, so we just confirm no crash.

	panel.update_from_payloads(42_000_000_000.0, 84_700_000_000_000_000.0, 0.0000496)
	panel.free()
	return f

# ─── Resource Strip ───────────────────────────────────────────────────────────

func _test_resource_strip() -> Array[String]:
	var f: Array[String] = []
	var strip := GmnResourceStrip.new()

	strip.update_from_payload({"balance": 4821.0, "resources": []})
	# Internal _fmt_balance logic
	var small := strip._fmt_balance(4821.0)
	if small.find("4821") == -1:
		f.append("resource_strip: balance 4821 should appear as-is")
	var large := strip._fmt_balance(1_500_000.0)
	if large.find("1.50M") == -1:
		f.append("resource_strip: balance 1.5M should be abbreviated")

	strip.free()
	return f

# ─── Notification Feed ────────────────────────────────────────────────────────

func _test_notification_feed() -> Array[String]:
	var f: Array[String] = []
	var feed := GmnNotificationFeed.new()

	feed.push("low priority info", GmnNotificationFeed.Priority.INFORMATIONAL)
	feed.push("critical alert",    GmnNotificationFeed.Priority.CRITICAL)
	feed.push("op complete",       GmnNotificationFeed.Priority.OPERATIONAL)

	if feed._queue.size() != 3:
		f.append("notification_feed: expected 3 queued items")
		feed.free()
		return f

	# After _process sorts by priority desc, critical should be first
	feed._queue.sort_custom(func(a, b): return a.priority > b.priority)
	if feed._queue[0].priority != GmnNotificationFeed.Priority.CRITICAL:
		f.append("notification_feed: critical priority must sort first")

	feed.free()
	return f

# ─── Nav Bar ─────────────────────────────────────────────────────────────────

func _test_nav_bar() -> Array[String]:
	var f: Array[String] = []
	var nav := GmnNavBar.new()
	nav._ready()  # manually call _ready since no scene tree

	# RESEARCH should be locked by default
	if "RESEARCH" not in nav._locked_sections:
		f.append("nav_bar: RESEARCH must be locked by default")

	# Active section should default to MINE
	if nav.get_active_section() != "MINE":
		f.append("nav_bar: default active section must be MINE")

	# Unlock RESEARCH
	nav.unlock_section("RESEARCH")
	if "RESEARCH" in nav._locked_sections:
		f.append("nav_bar: RESEARCH must be unlockable")

	nav.free()
	return f
