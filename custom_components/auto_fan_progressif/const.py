"""Constants for the Auto Fan Progressif integration."""

from __future__ import annotations

DOMAIN = "auto_fan_progressif"
CONF_VTHERM_ENTITY_ID = "vtherm_entity_id"
CONF_CLIMATE_ENTITY_ID = "climate_entity_id"
CONF_FAN_MODE_ORDER = "fan_mode_order"
DEFAULT_FAN_MODE_ORDER = ["quiet", "auto", "low", "middle", "medium", "high", "turbo"]
DEFAULT_DELTA_THRESHOLDS = [0.5, 1.0, 2.0, 3.0]
