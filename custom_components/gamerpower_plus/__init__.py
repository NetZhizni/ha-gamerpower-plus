"""The GamerPower Plus integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .api import async_create_client
from .const import DOMAIN
from .coordinator import (
    GamerPowerConfigEntry,
    GamerPowerCoordinator,
    async_remove_seen_store,
)
from .services import async_setup_services

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CALENDAR,
    Platform.EVENT,
    Platform.SENSOR,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration services once."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GamerPowerConfigEntry) -> bool:
    """Set up GamerPower Plus from a config entry."""
    coordinator = GamerPowerCoordinator(hass, entry, async_create_client(hass))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(coordinator.async_enable_new_giveaway_dispatch())
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GamerPowerConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: GamerPowerConfigEntry) -> None:
    """Delete the stored seen IDs when the entry is removed."""
    await async_remove_seen_store(hass, entry.entry_id)
