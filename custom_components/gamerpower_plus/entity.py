"""Base entity and helpers for GamerPower Plus."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.json import json_bytes
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONFIGURATION_URL,
    DOMAIN,
    MANUFACTURER,
    MAX_ATTRIBUTES_BYTES,
    RESERVED_ATTRIBUTES_BYTES,
)
from .coordinator import GamerPowerCoordinator


class GamerPowerEntity(CoordinatorEntity[GamerPowerCoordinator]):
    """An entity belonging to the device of a GamerPower Plus entry."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: GamerPowerCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=CONFIGURATION_URL,
        )


def build_list_attributes(
    key: str,
    items: Sequence[Mapping[str, Any]],
    extra: Mapping[str, Any] | None = None,
    max_bytes: int = MAX_ATTRIBUTES_BYTES - RESERVED_ATTRIBUTES_BYTES,
) -> dict[str, Any]:
    """Return attributes holding as many items as fit in ``max_bytes`` of JSON.

    ``truncated`` tells whether items were dropped from the end of the list.
    """
    base = {**(extra or {}), "truncated": True, key: []}
    size = len(json_bytes(base))
    kept: list[Mapping[str, Any]] = []
    for item in items:
        # One separator byte per item besides the item itself.
        item_size = len(json_bytes(item)) + 1
        if size + item_size > max_bytes:
            break
        size += item_size
        kept.append(item)
    return {
        **(extra or {}),
        "truncated": len(kept) < len(items),
        key: kept,
    }
