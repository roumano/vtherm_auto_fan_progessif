"""Constants for the Auto Fan Progressif integration."""

DOMAIN = "auto_fan_progressif"
CONF_FAN_MODE_ORDER = "fan_mode_order"
CONF_DELTA_THRESHOLDS = "delta_thresholds"
DEFAULT_FAN_MODE_ORDER = [
    "quiet",
    "auto",
    "low",
    "middle",
    "medium",
    "high",
    "turbo",
]
DEFAULT_DELTA_THRESHOLDS = [0.5, 1.0, 2.0, 3.0]
