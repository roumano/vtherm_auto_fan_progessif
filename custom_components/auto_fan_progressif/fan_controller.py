"""VTherm-linked progressive fan controller."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import Context, Event, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from vtherm_api import PluginClimate
from vtherm_api.const import EventType

from .const import CONF_CLIMATE_ENTITY_ID, CONF_FAN_MODE_ORDER
from .progressive_fan import choose_fan_mode


@dataclass(slots=True)
class FanModeSnapshot:
    current_temperature: float | None
    target_temperature: float | None
    hvac_mode: str | None
    fan_mode: str | None
    fan_modes: list[str]


class AutoFanProgressifPlugin(PluginClimate):
    """Subscribe to VTherm events and drive the underlying climate fan mode."""

    def __init__(self, hass: HomeAssistant, climate_entity_id: str, fan_mode_order: Iterable[str] | None = None) -> None:
        super().__init__(hass)
        self._climate_entity_id = climate_entity_id
        self._fan_mode_order = list(fan_mode_order or [])
        self._last_applied_mode: str | None = None
        self._climate_listener_remove = None

    @property
    def climate_entity_id(self) -> str:
        return self._climate_entity_id

    def link_to_vtherm(self, vtherm: Any) -> None:
        """Link to one VTherm thermostat and start listening to its events."""

        super().link_to_vtherm(vtherm)
        self._listen_to_target_climate_state()

    def remove_listeners(self) -> None:
        """Remove all listeners on unload."""

        if self._climate_listener_remove is not None:
            self._climate_listener_remove()
            self._climate_listener_remove = None
        super().remove_listeners()

    def handle_temperature_event(self, event: Event) -> None:
        self._maybe_schedule_apply(event)

    def handle_hvac_mode_event(self, event: Event) -> None:
        self._maybe_schedule_apply(event)

    def handle_preset_event(self, event: Event) -> None:
        self._maybe_schedule_apply(event)

    def _listen_to_target_climate_state(self) -> None:
        """Keep a fallback listener on the target climate entity."""

        if self._climate_listener_remove is not None:
            self._climate_listener_remove()
            self._climate_listener_remove = None

        self._climate_listener_remove = async_track_state_change_event(
            self._hass,
            [self._climate_entity_id],
            self._handle_target_climate_state_change,
        )

    async def _handle_target_climate_state_change(self, event: Event) -> None:
        """Fallback when the underlying climate changes outside VTherm events."""

        await self.async_apply_now(reason="target_state_change")

    def _maybe_schedule_apply(self, event: Event) -> None:
        self._hass.async_create_task(self.async_apply_now(reason=event.event_type))

    async def async_apply_now(self, reason: str | None = None, context: Context | None = None) -> str | None:
        """Evaluate current data and push the best fan mode to the climate."""

        snapshot = self._build_snapshot()
        if snapshot.current_temperature is None or snapshot.target_temperature is None:
            return None
        if snapshot.hvac_mode in {"off", "fan_only", None}:
            return None
        if not snapshot.fan_modes:
            return None

        decision = choose_fan_mode(
            snapshot.current_temperature,
            snapshot.target_temperature,
            snapshot.fan_modes,
            self._fan_mode_order or None,
        )
        selected_mode = decision.selected_mode
        if selected_mode is None:
            return None

        current_mode = snapshot.fan_mode.lower().strip() if snapshot.fan_mode else None
        if current_mode == selected_mode:
            self._last_applied_mode = selected_mode
            return selected_mode

        if self._last_applied_mode == selected_mode and current_mode == selected_mode:
            return selected_mode

        await self._hass.services.async_call(
            CLIMATE_DOMAIN,
            "set_fan_mode",
            {
                "entity_id": self._climate_entity_id,
                "fan_mode": selected_mode,
            },
            blocking=False,
            context=context,
        )
        self._last_applied_mode = selected_mode
        return selected_mode

    def _build_snapshot(self) -> FanModeSnapshot:
        state = self._hass.states.get(self._climate_entity_id)
        if state is None:
            return FanModeSnapshot(None, None, None, None, [])

        attrs = state.attributes
        raw_fan_modes = attrs.get("fan_modes") or []
        fan_modes = [str(mode).strip().lower() for mode in raw_fan_modes if str(mode).strip()]

        return FanModeSnapshot(
            current_temperature=_as_float(attrs.get("current_temperature")),
            target_temperature=_as_float(attrs.get(ATTR_TEMPERATURE)),
            hvac_mode=str(attrs.get("hvac_mode") or state.state).lower() if attrs.get("hvac_mode") or state.state else None,
            fan_mode=str(attrs.get("fan_mode")).lower() if attrs.get("fan_mode") else None,
            fan_modes=fan_modes,
        )


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
