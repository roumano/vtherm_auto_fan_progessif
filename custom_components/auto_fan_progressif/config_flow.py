"""Config flow for Auto Fan Progressif."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_AUTO_APPLY_ON_HVAC_MODE,
    CONF_CLIMATE_ENTITY_ID,
    CONF_FAN_MODE_ORDER,
    CONF_VTHERM_ENTITY_ID,
    DEFAULT_FAN_MODE_ORDER,
    DOMAIN,
)


class AutoFanProgressifConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for this integration."""

    VERSION = 1

    async def async_step_user(self, user_input: Mapping[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            vtherm_entity_id = str(user_input[CONF_VTHERM_ENTITY_ID]).strip()
            climate_entity_id = str(user_input[CONF_CLIMATE_ENTITY_ID]).strip()
            fan_mode_order = _parse_order(str(user_input.get(CONF_FAN_MODE_ORDER, "")))
            auto_apply = bool(user_input.get(CONF_AUTO_APPLY_ON_HVAC_MODE, True))

            if not vtherm_entity_id or not climate_entity_id:
                errors["base"] = "missing_entity"
            else:
                return self.async_create_entry(
                    title=f"Auto Fan Progressif - {vtherm_entity_id}",
                    data={
                        CONF_VTHERM_ENTITY_ID: vtherm_entity_id,
                        CONF_CLIMATE_ENTITY_ID: climate_entity_id,
                        CONF_FAN_MODE_ORDER: fan_mode_order,
                        CONF_AUTO_APPLY_ON_HVAC_MODE: auto_apply,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_VTHERM_ENTITY_ID): str,
                vol.Required(CONF_CLIMATE_ENTITY_ID): str,
                vol.Required(
                    CONF_FAN_MODE_ORDER,
                    default=", ".join(DEFAULT_FAN_MODE_ORDER),
                ): str,
                vol.Required(CONF_AUTO_APPLY_ON_HVAC_MODE, default=True): bool,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)


def _parse_order(raw: str) -> list[str]:
    values = [item.strip().lower() for item in raw.split(",")]
    return [item for item in values if item]
