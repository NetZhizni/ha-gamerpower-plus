"""Binary sensor for GamerPower Plus."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util import dt as dt_util

from .api import Giveaway
from .coordinator import GamerPowerConfigEntry, GamerPowerCoordinator
from .entity import GamerPowerEntity, build_list_attributes

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GamerPowerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensor."""
    async_add_entities([ExpiringSoonBinarySensor(entry.runtime_data)])


class ExpiringSoonBinarySensor(GamerPowerEntity, BinarySensorEntity):
    """On while a giveaway ends within the configured number of hours."""

    _unrecorded_attributes = frozenset({"giveaways", "truncated"})

    def __init__(self, coordinator: GamerPowerCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, "expiring_soon")
        self._unsub_timer: CALLBACK_TYPE | None = None

    def _expiring(self, now: datetime) -> list[Giveaway]:
        limit = now + self.coordinator.expiring_threshold
        expiring = [
            g
            for g in self.coordinator.data.giveaways
            if g.end_date is not None and now < g.end_date <= limit
        ]
        return sorted(expiring, key=lambda g: g.end_date or now)

    @property
    def is_on(self) -> bool:
        """Return True if a giveaway expires soon."""
        return bool(self._expiring(dt_util.utcnow()))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the giveaways that expire soon."""
        return build_list_attributes(
            "giveaways",
            [g.as_compact_dict() for g in self._expiring(dt_util.utcnow())],
            {
                "threshold_hours": self.coordinator.expiring_threshold.total_seconds()
                / 3600
            },
        )

    async def async_added_to_hass(self) -> None:
        """Schedule the first state change."""
        await super().async_added_to_hass()
        self._schedule_next_change()

    async def async_will_remove_from_hass(self) -> None:
        """Cancel the timer."""
        await super().async_will_remove_from_hass()
        self._cancel_timer()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._schedule_next_change()
        super()._handle_coordinator_update()

    @callback
    def _cancel_timer(self) -> None:
        if self._unsub_timer is not None:
            self._unsub_timer()
            self._unsub_timer = None

    @callback
    def _schedule_next_change(self) -> None:
        """Re-evaluate when a giveaway enters the window or expires."""
        self._cancel_timer()
        if self.coordinator.data is None:
            return
        now = dt_util.utcnow()
        threshold = self.coordinator.expiring_threshold
        moments = [
            moment
            for g in self.coordinator.data.giveaways
            if g.end_date is not None
            for moment in (g.end_date - threshold, g.end_date)
            if moment > now
        ]
        if moments:
            self._unsub_timer = async_track_point_in_utc_time(
                self.hass, self._handle_timer, min(moments)
            )

    @callback
    def _handle_timer(self, _now: datetime) -> None:
        self._unsub_timer = None
        self._schedule_next_change()
        self.async_write_ha_state()
