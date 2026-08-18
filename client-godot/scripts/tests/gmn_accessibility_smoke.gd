extends RefCounted
class_name GmnAccessibilitySmoke

func run() -> Dictionary:
	var settings := GmnAccessibilitySettings.new()
	var failures: Array[String] = []
	settings.set_ui_scale(3.0)
	settings.set_text_scale(0.5)
	settings.set_color_mode("deuteranopia")
	settings.toggle_reduce_motion()
	var display := settings.to_display()
	if display.get("ui_scale") != 2.0:
		failures.append("UI scale was not clamped")
	if display.get("text_scale") != 0.75:
		failures.append("text scale was not clamped")
	if display.get("color_mode") != "deuteranopia":
		failures.append("color mode did not persist")
	if display.get("reduce_motion") != true:
		failures.append("reduce motion did not toggle")
	return {"ok": failures.is_empty(), "failures": failures}
