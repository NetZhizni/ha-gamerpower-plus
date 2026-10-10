"""Sensors for GamerPower Plus."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import GamerPowerConfigEntry, GamerPowerCoordinator
from .entity import GamerPowerEntity, build_list_attributes

PARALLEL_UPDATES = 0

_MAX_STATE_LENGTH = 255


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GamerPowerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            ActiveGiveawaysSensor(coordinator),
            TotalWorthSensor(coordinator),
            LatestGiveawaySensor(coordinator),
        ]
    )


class ActiveGiveawaysSensor(GamerPowerEntity, SensorEntity):
    """Number of active giveaways after all filters."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _unrecorded_attributes = frozenset({"giveaways", "truncated"})

    def __init__(self, coordinator: GamerPowerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "active_giveaways")

    @property
    def native_value(self) -> int:
        """Return the number of giveaways."""
        return len(self.coordinator.data.giveaways)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return a compact list of giveaways, limited in size."""
        return build_list_attributes(
            "giveaways",
            [g.as_compact_dict() for g in self.coordinator.data.giveaways],
        )


class TotalWorthSensor(GamerPowerEntity, SensorEntity):
    """Sum of the known worth of the listed giveaways."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = "USD"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: GamerPowerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "total_worth")

    @property
    def native_value(self) -> float:
        """Return the total worth in USD."""
        return self.coordinator.data.total_worth

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return how many giveaways have a known worth."""
        giveaways = self.coordinator.data.giveaways
        unknown = sum(1 for g in giveaways if g.worth_value is None)
        return {
            "giveaways_with_worth": len(giveaways) - unknown,
            "giveaways_without_worth": unknown,
        }


class LatestGiveawaySensor(GamerPowerEntity, SensorEntity):
    """Title of the most recently published giveaway."""

    _unrecorded_attributes = frozenset(
        {
            "description",
            "instructions",
            "image",
            "thumbnail",
            "open_giveaway_url",
            "gamerpower_url",
            "users",
        }
    )

    def __init__(self, coordinator: GamerPowerCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "latest_giveaway")

    @property
    def native_value(self) -> str | None:
        """Return the title of the latest giveaway."""
        if (latest := self.coordinator.data.latest) is None:
            return None
        return latest.title[:_MAX_STATE_LENGTH]

    @property
    def entity_picture(self) -> str | None:
        """Return the thumbnail of the latest giveaway."""
        if (latest := self.coordinator.data.latest) is None:
            return None
        return latest.thumbnail or None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return all fields of the latest giveaway."""
        if (latest := self.coordinator.data.latest) is None:
            return None
        return latest.as_dict()
