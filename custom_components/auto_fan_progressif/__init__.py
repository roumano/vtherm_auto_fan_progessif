"""Auto Fan Progressif.

Minimal external integration skeleton for Versatile Thermostat.
The progressive selection logic lives in progressive_fan.py.

This file is intentionally conservative: it exposes the package structure and
leaves the VTherm event wiring to the next implementation step.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN

PLATFORMS: list[str] = []


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration from YAML (unused placeholder)."""

    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an entry.

    The next step is to connect a VTherm-linked climate helper here.
    """

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "entry": entry,
        "controller_factory": _build_controller_factory,
    }
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an entry."""

    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return True


def _build_controller_factory() -> Callable[..., Any]:
    """Return a placeholder factory for the next implementation step."""

    def _factory(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"args": args, "kwargs": kwargs}

    return _factory
