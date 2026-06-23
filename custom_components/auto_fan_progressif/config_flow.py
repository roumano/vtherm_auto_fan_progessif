"""Config flow for Auto Fan Progressif."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
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

            if not vtherm_entity_id or not climate_entity_id:
                errors["base"] = "missing_entity"
            else:
                return self.async_create_entry(
                    title=f"Auto Fan Progressif - {vtherm_entity_id}",
                    data={
                        CONF_VTHERM_ENTITY_ID: vtherm_entity_id,
                        CONF_CLIMATE_ENTITY_ID: climate_entity_id,
                        CONF_FAN_MODE_ORDER: fan_mode_order,
                    },
                )

        return self._show_form(errors=errors)

    @staticmethod
    def _schema(
        *,
        vtherm_entity_id: str = "",
        climate_entity_id: str = "",
        fan_mode_order: str | None = None,
    ) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_VTHERM_ENTITY_ID, default=vtherm_entity_id): str,
                vol.Required(CONF_CLIMATE_ENTITY_ID, default=climate_entity_id): str,
                vol.Required(
                    CONF_FAN_MODE_ORDER,
                    default=fan_mode_order if fan_mode_order is not None else ", ".join(DEFAULT_FAN_MODE_ORDER),
                ): str,
            }
        )

    def _show_form(self, *, errors: dict[str, str], fan_mode_order: str | None = None) -> FlowResult:
        return self.async_show_form(
            step_id="user",
            data_schema=self._schema(fan_mode_order=fan_mode_order),
            errors=errors,
        )



def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "AutoFanProgressifOptionsFlowHandler":
    """Return the options flow handler."""

    return AutoFanProgressifOptionsFlowHandler(config_entry)


class AutoFanProgressifOptionsFlowHandler(config_entries.OptionsFlowWithConfigEntry):
    """Options flow for the integration."""

    async def async_step_init(self, user_input: Mapping[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        current_vtherm = str(self.config_entry.data.get(CONF_VTHERM_ENTITY_ID, "")).strip()
        current_climate = str(self.config_entry.data.get(CONF_CLIMATE_ENTITY_ID, "")).strip()
        current_order = self.config_entry.options.get(
            CONF_FAN_MODE_ORDER,
            self.config_entry.data.get(CONF_FAN_MODE_ORDER, DEFAULT_FAN_MODE_ORDER),
        )

        if user_input is not None:
            vtherm_entity_id = str(user_input[CONF_VTHERM_ENTITY_ID]).strip()
            climate_entity_id = str(user_input[CONF_CLIMATE_ENTITY_ID]).strip()
            fan_mode_order = _parse_order(str(user_input.get(CONF_FAN_MODE_ORDER, "")))

            if not vtherm_entity_id or not climate_entity_id:
                errors["base"] = "missing_entity"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_VTHERM_ENTITY_ID: vtherm_entity_id,
                        CONF_CLIMATE_ENTITY_ID: climate_entity_id,
                        CONF_FAN_MODE_ORDER: fan_mode_order,
                    },
                )

        return self.async_show_form(
            step_id="init",
            data_schema=AutoFanProgressifConfigFlow._schema(
                vtherm_entity_id=current_vtherm,
                climate_entity_id=current_climate,
                fan_mode_order=", ".join(current_order) if isinstance(current_order, list) else str(current_order),
            ),
            errors=errors,
        )


def _parse_order(raw: str) -> list[str]:
    values = [item.strip().lower() for item in raw.split(",")]
    return [item for item in values if item]
