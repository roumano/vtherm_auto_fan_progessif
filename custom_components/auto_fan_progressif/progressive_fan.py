"""Progressive auto-fan selection helpers.

This module is intentionally pure so it can be unit-tested without Home Assistant.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .const import DEFAULT_DELTA_THRESHOLDS, DEFAULT_FAN_MODE_ORDER

@dataclass(frozen=True)
class ProgressiveFanDecision:
    """Result returned by the progressive selector."""

    delta: float
    ordered_modes: tuple[str, ...]
    selected_index: int
    selected_mode: str | None


def _dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = str(value).strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def normalize_supported_modes(
    fan_modes: Sequence[str] | None,
    preferred_order: Sequence[str] | None = None,
) -> list[str]:
    """Return fan modes ordered from quietest to strongest.

    Only the modes explicitly listed in preferred_order are used.
    Any other supported modes are ignored on purpose, so the plugin
    never falls back to an unexpected mode such as ``auto``.
    """

    supported = _dedupe_preserve_order(fan_modes or [])
    if not supported:
        return []

    order = _dedupe_preserve_order(preferred_order or DEFAULT_FAN_MODE_ORDER)

    # Strict mode: only keep modes explicitly declared in the order.
    return [mode for mode in order if mode in supported]


def select_progressive_index(delta: float, mode_count: int) -> int:
    """Map a temperature delta to a target fan index.

    Rules requested by the user:
      - delta < 0.5  -> quietest mode
      - delta < 1.0  -> 2nd quietest mode
      - delta < 2.0  -> 3rd quietest mode
      - delta < 3.0  -> 4th quietest mode
      - delta >= 3.0 -> strongest mode

    The result is clamped to the available mode count.
    """

    if mode_count <= 0:
        return -1

    abs_delta = abs(float(delta))
    if abs_delta < DEFAULT_DELTA_THRESHOLDS[0]:
        idx = 0
    elif abs_delta < DEFAULT_DELTA_THRESHOLDS[1]:
        idx = 1
    elif abs_delta < DEFAULT_DELTA_THRESHOLDS[2]:
        idx = 2
    elif abs_delta < DEFAULT_DELTA_THRESHOLDS[3]:
        idx = 3
    else:
        idx = mode_count - 1

    return max(0, min(idx, mode_count - 1))


def delta_band(delta: float) -> str:
    """Return a human-friendly band name for logs."""

    abs_delta = abs(float(delta))
    if abs_delta < DEFAULT_DELTA_THRESHOLDS[0]:
        return "quietest"
    if abs_delta < DEFAULT_DELTA_THRESHOLDS[1]:
        return "low"
    if abs_delta < DEFAULT_DELTA_THRESHOLDS[2]:
        return "medium"
    if abs_delta < DEFAULT_DELTA_THRESHOLDS[3]:
        return "high"
    return "max"


def choose_fan_mode(
    current_temperature: float,
    target_temperature: float,
    fan_modes: Sequence[str] | None,
    preferred_order: Sequence[str] | None = None,
) -> ProgressiveFanDecision:
    """Choose the best fan mode for the current delta."""

    ordered_modes = normalize_supported_modes(fan_modes, preferred_order)
    delta = abs(float(current_temperature) - float(target_temperature))
    selected_index = select_progressive_index(delta, len(ordered_modes))

    return ProgressiveFanDecision(
        delta=delta,
        ordered_modes=tuple(ordered_modes),
        selected_index=selected_index,
        selected_mode=None if selected_index < 0 else ordered_modes[selected_index],
    )
