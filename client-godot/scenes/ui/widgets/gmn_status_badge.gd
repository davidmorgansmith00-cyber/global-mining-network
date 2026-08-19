## GMN Status Badge
## Shared presentation widget for operational status indicators.
## Colour + text symbol always used together (never colour alone) for accessibility.
## badge_key maps to one of the STATUS_CONFIGS entries.

extends Label
class_name GmnStatusBadge

const STATUS_CONFIGS := {
	"mining":    {"text": "● MINING",      "colour": "success"},
	"idle":      {"text": "◌ IDLE",         "colour": "secondary"},
	"throttled": {"text": "⚠ THROTTLED",   "colour": "warning"},
	"offline":   {"text": "✕ OFFLINE",      "colour": "danger"},
	"upgrading": {"text": "⚙ UPGRADING",   "colour": "primary"},
	"overheat":  {"text": "🔥 OVERHEAT",   "colour": "danger"},
	"error":     {"text": "✕ ERROR",        "colour": "danger"},
	"unknown":   {"text": "? UNKNOWN",      "colour": "secondary"},
}

const COLOUR_MAP := {
	"primary":   GmnUiTokens.ACCENT_PRIMARY,
	"success":   GmnUiTokens.ACCENT_SUCCESS,
	"warning":   GmnUiTokens.ACCENT_WARNING,
	"danger":    GmnUiTokens.ACCENT_DANGER,
	"secondary": GmnUiTokens.TEXT_SECONDARY,
}

func set_badge(badge_key: String) -> void:
	var key := badge_key.to_lower()
	var config: Dictionary = STATUS_CONFIGS.get(key, STATUS_CONFIGS["unknown"])
	text = config["text"]
	add_theme_color_override("font_color", COLOUR_MAP.get(config["colour"], GmnUiTokens.TEXT_SECONDARY))
