"""Event entity for GamerPower Plus."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import EVENT_TYPE_NEW_GIVEAWAY, signal_new_giveaway
from .coordinator import GamerPowerConfigEntry, GamerPowerCoordinator
from .entity import GamerPowerEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GamerPowerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the event entity."""
    async_add_entities([NewGiveawayEvent(entry.runtime_data)])


class NewGiveawayEvent(GamerPowerEntity, EventEntity):
    """Fires once for every new giveaway."""

    _unrecorded_attributes = frozenset(
        {"description", "instructions", "image", "thumbnail"}
    )

    def __init__(self, coordinator: GamerPowerCoordinator) -> None:
        """Initialize the event entity."""
        super().__init__(coordinator, "new_giveaway")
        self._attr_event_types = [EVENT_TYPE_NEW_GIVEAWAY]

    async def async_added_to_hass(self) -> None:
        """Listen for new giveaways of this entry."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                signal_new_giveaway(self.coordinator.config_entry.entry_id),
                self._async_handle_new_giveaway,
            )
        )

    @callback
    def _async_handle_new_giveaway(self, payload: dict[str, Any]) -> None:
        self._trigger_event(EVENT_TYPE_NEW_GIVEAWAY, payload)
        self.async_write_ha_state()
