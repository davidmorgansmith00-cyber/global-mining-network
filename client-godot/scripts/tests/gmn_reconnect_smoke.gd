extends RefCounted
class_name GmnReconnectSmoke

# Uses a local stream client instance to validate cursor monotonicity behavior.
func run() -> Dictionary:
	var stream := GmnStreamClient.new()
	stream.set_cursor(0)
	stream.acknowledge_cursor(4)
	stream.acknowledge_cursor(2)
	stream.acknowledge_cursor(9)

	var failures: Array[String] = []
	if stream.reconnect_cursor != 9:
		failures.append("expected reconnect cursor 9, got %d" % stream.reconnect_cursor)

	stream.set_cursor(3)
	if stream.reconnect_cursor != 3:
		failures.append("expected reconnect cursor 3 after explicit set, got %d" % stream.reconnect_cursor)

	return {
		"ok": failures.is_empty(),
		"failures": failures,
	}
