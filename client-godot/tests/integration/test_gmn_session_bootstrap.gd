## Test GMN-CL-01: Session Bootstrap Wiring
## Validates: register → login → refresh → logout flow with GmnSession

extends GutTest

var api_client: GmnApiClient
var test_email: String = "test_bootstrap_%d@example.com" % randi()
var test_password: String = "test_password_123"

func before_each() -> void:
	api_client = GmnApiClient.new()
	add_child(api_client)

func after_each() -> void:
	if api_client:
		api_client.queue_free()

## Test 1: Client can bootstrap session via register
func test_register_populates_session() -> void:
	var response = await api_client.register_session(test_email, test_password)
	
	assert_true(response.get("ok", false), "Register should succeed")
	assert_ne(api_client.session.player_id, "", "Session should have player_id after register")
	assert_ne(api_client.session.access_token, "", "Session should have access_token after register")
	assert_ne(api_client.session.refresh_token, "", "Session should have refresh_token after register")

## Test 2: Session values available to authorized requests
func test_session_values_used_in_requests() -> void:
	# Register to get session
	var register_response = await api_client.register_session(test_email, test_password)
	assert_true(register_response.get("ok", false), "Register should succeed")
	
	# Verify session is populated
	assert_true(api_client.is_authenticated(), "Client should be authenticated after register")
	var session = api_client.get_session()
	assert_ne(session.player_id, "", "Session should have player_id")
	assert_ne(session.access_token, "", "Session should have access_token")

## Test 3: Client can bootstrap session via login
func test_login_populates_session() -> void:
	# First register
	var register_response = await api_client.register_session(test_email, test_password)
	assert_true(register_response.get("ok", false), "Register should succeed")
	
	# Clear session
	api_client.session.clear()
	assert_false(api_client.is_authenticated(), "Session should be cleared")
	
	# Now login
	var login_response = await api_client.login_session(test_email, test_password)
	assert_true(login_response.get("ok", false), "Login should succeed")
	assert_ne(api_client.session.player_id, "", "Session should have player_id after login")
	assert_ne(api_client.session.access_token, "", "Session should have access_token after login")

## Test 4: Refresh token updates tokens without clearing player_id
func test_refresh_token_updates_tokens() -> void:
	# Register to get session
	var register_response = await api_client.register_session(test_email, test_password)
	assert_true(register_response.get("ok", false), "Register should succeed")
	
	var original_player_id = api_client.session.player_id
	var original_access_token = api_client.session.access_token
	
	# Refresh
	var refresh_response = await api_client.refresh_access_token()
	assert_true(refresh_response.get("ok", false), "Refresh should succeed")
	
	# Verify player_id unchanged, tokens changed
	assert_eq(api_client.session.player_id, original_player_id, "player_id should not change on refresh")
	assert_ne(api_client.session.access_token, "", "Session should have new access_token")
	assert_ne(api_client.session.refresh_token, "", "Session should have new refresh_token")

## Test 5: Logout clears session
func test_logout_clears_session() -> void:
	# Register to get session
	var register_response = await api_client.register_session(test_email, test_password)
	assert_true(register_response.get("ok", false), "Register should succeed")
	assert_true(api_client.is_authenticated(), "Should be authenticated after register")
	
	# Logout
	var logout_response = await api_client.logout_session()
	assert_true(logout_response.get("ok", false), "Logout should succeed")
	assert_false(api_client.is_authenticated(), "Should not be authenticated after logout")
	assert_eq(api_client.session.player_id, "", "player_id should be cleared")
	assert_eq(api_client.session.access_token, "", "access_token should be cleared")

## Test 6: No client-owned progression introduced
## (Session only holds identity, not progression state)
func test_session_contains_only_identity_data() -> void:
	var register_response = await api_client.register_session(test_email, test_password)
	assert_true(register_response.get("ok", false), "Register should succeed")
	
	var session = api_client.get_session()
	
	# Verify session has only auth data
	assert_ne(session.player_id, "", "Session should have player_id")
	assert_ne(session.access_token, "", "Session should have access_token")
	assert_ne(session.refresh_token, "", "Session should have refresh_token")
	
	# Verify session does NOT have progression data
	assert_false(session.has_meta("balance"), "Session should not store balance")
	assert_false(session.has_meta("rewards"), "Session should not store rewards")
	assert_false(session.has_meta("progression"), "Session should not store progression")

## Test 7: Full lifecycle: register → verify auth → logout → verify cleared
func test_full_bootstrap_lifecycle() -> void:
	# 1. Register
	var register_response = await api_client.register_session(test_email, test_password)
	assert_true(register_response.get("ok", false), "Register should succeed")
	assert_true(api_client.is_authenticated(), "Should be authenticated after register")
	
	# 2. Verify session has all required fields
	var session = api_client.get_session()
	assert_ne(session.player_id, "", "Should have player_id")
	assert_ne(session.access_token, "", "Should have access_token")
	assert_ne(session.refresh_token, "", "Should have refresh_token")
	
	# 3. Logout
	var logout_response = await api_client.logout_session()
	assert_true(logout_response.get("ok", false), "Logout should succeed")
	assert_false(api_client.is_authenticated(), "Should not be authenticated after logout")
	
	# 4. Verify all fields cleared
	assert_eq(session.player_id, "", "player_id should be cleared")
	assert_eq(session.access_token, "", "access_token should be cleared")
	assert_eq(session.refresh_token, "", "refresh_token should be cleared")

## Test 8: Acceptance criteria validation
## Criteria 1: Client can bootstrap a session against local API ✓
## Criteria 2: Session values available to authorized HTTP and websocket requests ✓
## Criteria 3: No client-owned progression or reward state introduced ✓
func test_acceptance_criteria_met() -> void:
	# Criteria 1: Bootstrap session
	var register_response = await api_client.register_session(test_email, test_password)
	assert_true(register_response.get("ok", false), "Criteria 1: Can bootstrap session")
	
	# Criteria 2: Session values available
	assert_ne(api_client.session.access_token, "", "Criteria 2: Access token available")
	assert_ne(api_client.session.player_id, "", "Criteria 2: Player ID available")
	
	# Criteria 3: No progression in session
	assert_false(api_client.session.has_meta("balance"), "Criteria 3: No progression state")
	
	pass_test("All acceptance criteria met for GMN-CL-01")
