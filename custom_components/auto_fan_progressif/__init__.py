"""Auto Fan Progressif.

External integration for Versatile Thermostat using vtherm_api.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from vtherm_api import VThermAPI

from .const import (
    CONF_AUTO_APPLY_ON_HVAC_MODE,
    CONF_CLIMATE_ENTITY_ID,
    CONF_FAN_MODE_ORDER,
    CONF_VTHERM_ENTITY_ID,
    DOMAIN,
)
from .fan_controller import AutoFanProgressifPlugin

PLATFORMS: list[str] = []

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration from YAML if needed."""

    hass.data.setdefault(DOMAIN, {})
    _LOGGER.debug("async_setup called for %s", DOMAIN)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Auto Fan Progressif from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    api = VThermAPI.get_vtherm_api(hass)
    if api is None:
        _LOGGER.error("VThermAPI is not available; cannot initialize %s", DOMAIN)
        return False

    vtherm_entity_id = str(entry.data[CONF_VTHERM_ENTITY_ID])
    climate_entity_id = str(entry.data[CONF_CLIMATE_ENTITY_ID])
    fan_mode_order = entry.data.get(CONF_FAN_MODE_ORDER, [])

    _LOGGER.info(
        "Setting up %s for VTherm=%s climate=%s",
        DOMAIN,
        vtherm_entity_id,
        climate_entity_id,
    )
    _LOGGER.debug(
        "Config values for %s: fan_mode_order=%s auto_apply_on_hvac_mode=%s",
        entry.entry_id,
        fan_mode_order,
        entry.data.get(CONF_AUTO_APPLY_ON_HVAC_MODE, True),
    )

    plugin = AutoFanProgressifPlugin(hass, climate_entity_id, fan_mode_order)
    vtherm = _get_climate_entity(hass, vtherm_entity_id)
    if vtherm is None:
        _LOGGER.error("Unable to find VTherm climate entity: %s", vtherm_entity_id)
        return False

    plugin.link_to_vtherm(vtherm)

    hass.data[DOMAIN][entry.entry_id] = {
        "entry": entry,
        "api": api,
        "plugin": plugin,
        CONF_AUTO_APPLY_ON_HVAC_MODE: bool(entry.data.get(CONF_AUTO_APPLY_ON_HVAC_MODE, True)),
    }
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the config entry and remove listeners."""

    stored = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    plugin = stored.get("plugin") if stored else None
    if plugin is not None:
        _LOGGER.info("Unloading %s for entry=%s", DOMAIN, entry.entry_id)
        plugin.remove_listeners()
    return True


def _get_climate_entity(hass: HomeAssistant, entity_id: str) -> Any | None:
    component = hass.data.get("climate")
    if component is None:
        return None
    return component.get_entity(entity_id)
