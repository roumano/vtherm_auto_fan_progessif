"""VTherm-linked progressive fan controller."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import Context, Event, HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from vtherm_api import PluginClimate

from .const import DEFAULT_FAN_MODE_ORDER
from .progressive_fan import choose_fan_mode, delta_band

_LOGGER = logging.getLogger(__name__)


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
        self._climate_listener_remove = None
        self._remove_listener = None  # compatibility alias
        _LOGGER.debug(
            "AutoFanProgressifPlugin created for climate=%s preferred_order=%s",
            self._climate_entity_id,
            self._fan_mode_order,
        )

    @property
    def climate_entity_id(self) -> str:
        return self._climate_entity_id

    def link_to_vtherm(self, vtherm: Any) -> None:
        """Link to one VTherm thermostat and start listening to its events."""

        _LOGGER.info("Linking progressive auto-fan to VTherm for climate=%s", self._climate_entity_id)
        super().link_to_vtherm(vtherm)
        self._listen_to_target_climate_state()

    def remove_listeners(self) -> None:
        """Remove all listeners on unload."""

        _LOGGER.debug("Removing listeners for climate=%s", self._climate_entity_id)
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None

        self._last_applied_mode = None
        super().remove_listeners()

    def handle_temperature_event(self, event: Event) -> None:
        _LOGGER.debug("Received temperature event for %s: %s", self._climate_entity_id, event.data)
        self._maybe_schedule_apply(event)

    def handle_hvac_mode_event(self, event: Event) -> None:
        _LOGGER.debug("Received HVAC mode event for %s: %s", self._climate_entity_id, event.data)
        self._maybe_schedule_apply(event)

    def handle_preset_event(self, event: Event) -> None:
        _LOGGER.debug("Received preset event for %s: %s", self._climate_entity_id, event.data)
        self._maybe_schedule_apply(event)

    def _listen_to_target_climate_state(self) -> None:
        """Keep a fallback listener on the target climate entity."""

        if self._climate_listener_remove is not None:
            self._climate_listener_remove()
            self._climate_listener_remove = None
            self._remove_listener = None

        _LOGGER.debug("Listening for state changes on climate entity=%s", self._climate_entity_id)
        self._climate_listener_remove = async_track_state_change_event(
            self._hass,
            [self._climate_entity_id],
            self._handle_target_climate_state_change,
        )
        self._remove_listener = self._climate_listener_remove

    async def _handle_target_climate_state_change(self, event: Event) -> None:
        """Fallback when the underlying climate changes outside VTherm events."""

        _LOGGER.debug("Target climate state changed for %s: %s", self._climate_entity_id, event.data)
        await self.async_apply_now(reason="target_state_change")

    def _maybe_schedule_apply(self, event: Event) -> None:
        _LOGGER.debug(
            "Scheduling progressive auto-fan evaluation for %s because of %s",
            self._climate_entity_id,
            event.event_type,
        )
        self._hass.add_job(self.async_apply_now, reason=event.event_type)

    async def async_apply_now(self, reason: str | None = None, context: Context | None = None) -> str | None:
        """Evaluate current data and push the best fan mode to the climate."""
        current_fan_mode = self._climate.fan_mode
        if current_fan_mode != "auto":
            _LOGGER.debug(
                "Skip auto-fan for %s: fan_mode=%s (expected auto)",
                self._climate.entity_id,
                current_fan_mode,
            )
            self._last_applied_mode = None

        snapshot = self._build_snapshot()
        _LOGGER.debug(
            "Auto-fan snapshot for %s (reason=%s): current=%s target=%s hvac=%s fan_mode=%s fan_modes=%s",
            self._climate_entity_id,
            reason,
            snapshot.current_temperature,
            snapshot.target_temperature,
            snapshot.hvac_mode,
            snapshot.fan_mode,
            snapshot.fan_modes,
        )

        if snapshot.current_temperature is None or snapshot.target_temperature is None:
            _LOGGER.debug("Skipping auto-fan for %s: missing temperatures", self._climate_entity_id)
            return None
        if snapshot.hvac_mode in {"off", "fan_only", None}:
            _LOGGER.debug("Skipping auto-fan for %s: HVAC mode is %s", self._climate_entity_id, snapshot.hvac_mode)
            return None
        if not snapshot.fan_modes:
            _LOGGER.debug("Skipping auto-fan for %s: no fan_modes attribute available", self._climate_entity_id)
            return None

        preferred_order = self._fan_mode_order or list(DEFAULT_FAN_MODE_ORDER)
        preferred_set = set(preferred_order)
        ignored_modes = [mode for mode in snapshot.fan_modes if mode not in preferred_set]
        if ignored_modes:
            _LOGGER.debug(
                "Ignoring unsupported or non-ordered fan modes for %s: %s (preferred_order=%s)",
                self._climate_entity_id,
                ignored_modes,
                preferred_order,
            )

        decision = choose_fan_mode(
            snapshot.current_temperature,
            snapshot.target_temperature,
            snapshot.fan_modes,
            preferred_order,
        )
        selected_mode = decision.selected_mode
        if selected_mode is None:
            _LOGGER.debug("Skipping auto-fan for %s: no mode selected", self._climate_entity_id)
            return None

        current_mode = snapshot.fan_mode.lower().strip() if snapshot.fan_mode else None
        band = delta_band(decision.delta)

        _LOGGER.debug(
            "Decision for %s: delta=%.2f band=%s ordered_modes=%s selected=%s index=%s current=%s",
            self._climate_entity_id,
            decision.delta,
            band,
            list(decision.ordered_modes),
            selected_mode,
            decision.selected_index,
            current_mode,
        )

        if current_mode == selected_mode:
            _LOGGER.debug("No change for %s: already on fan mode %s", self._climate_entity_id, selected_mode)
            return selected_mode

        _LOGGER.info(
            "Applying progressive auto-fan on %s: %s -> %s (delta=%.2f, band=%s)",
            self._climate_entity_id,
            current_mode,
            selected_mode,
            decision.delta,
            band,
        )
        try:
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
        except Exception:
            _LOGGER.exception(
                "Failed to apply fan mode %s on %s",
                selected_mode,
                self._climate_entity_id,
            )
            raise

        return selected_mode

    def _build_snapshot(self) -> FanModeSnapshot:
        state = self._hass.states.get(self._climate_entity_id)
        if state is None:
            _LOGGER.debug("No state found for climate entity=%s", self._climate_entity_id)
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
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None
