"""Diagnostics for GamerPower Plus.

The entry holds no credentials or personal data: only filter settings and
public giveaway data are reported.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import GamerPowerConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: GamerPowerConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": repr(coordinator.last_exception)
            if coordinator.last_exception
            else None,
            "update_interval_seconds": coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None,
            "seen_ids": coordinator.seen_count,
        },
        "data": {
            "fetched_count": data.fetched_count,
            "filtered_count": len(data.giveaways),
            "total_worth": data.total_worth,
            "giveaways": [g.as_compact_dict() for g in data.giveaways],
        }
        if data
        else None,
    }
