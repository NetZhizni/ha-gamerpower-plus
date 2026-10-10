"""Tests for the GamerPower Plus services and diagnostics."""

from __future__ import annotations

import aiohttp
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.gamerpower_plus.const import (
    ATTR_CONFIG_ENTRY_ID,
    CONF_PLATFORMS,
    CONF_TYPES,
    DOMAIN,
    EVENT_NEW_GIVEAWAY,
)
from custom_components.gamerpower_plus.diagnostics import (
    async_get_config_entry_diagnostics,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .conftest import ENTRY_ID, make_giveaway, mock_filter, setup_entry


async def test_services_registered(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Services exist after setup."""
    mock_filter(aioclient_mock, [make_giveaway(1)])
    await setup_entry(hass, mock_config_entry)
    for service in ("refresh", "get_giveaways", "reset_seen"):
        assert hass.services.has_service(DOMAIN, service)


async def test_get_giveaways(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The response holds the filtered list with all fields."""
    mock_filter(aioclient_mock, [make_giveaway(1), make_giveaway(2, worth="N/A")])
    await setup_entry(hass, mock_config_entry)

    for data in ({}, {ATTR_CONFIG_ENTRY_ID: ENTRY_ID}):
        response = await hass.services.async_call(
            DOMAIN, "get_giveaways", data, blocking=True, return_response=True
        )
        assert len(response["entries"]) == 1
        entry = response["entries"][0]
        assert entry["config_entry_id"] == ENTRY_ID
        assert entry["count"] == 2
        assert entry["total_worth"] == 9.99
        assert entry["giveaways"][0]["id"] == 1
        assert entry["giveaways"][0]["instructions"]
        assert entry["giveaways"][1]["worth_value"] is None


async def test_refresh(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Refresh fetches again and reports failures."""
    mock_filter(aioclient_mock, [make_giveaway(1)])
    await setup_entry(hass, mock_config_entry)

    mock_filter(aioclient_mock, [make_giveaway(1), make_giveaway(2)])
    await hass.services.async_call(DOMAIN, "refresh", {}, blocking=True)
    assert aioclient_mock.call_count == 1
    assert len(mock_config_entry.runtime_data.data.giveaways) == 2

    mock_filter(aioclient_mock, exc=aiohttp.ClientConnectionError())
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, "refresh", {ATTR_CONFIG_ENTRY_ID: ENTRY_ID}, blocking=True
        )


async def test_refresh_all_entries(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Without an entry ID every loaded entry is refreshed."""
    other = MockConfigEntry(
        domain=DOMAIN,
        unique_id="gog|game",
        data={CONF_PLATFORMS: ["gog"], CONF_TYPES: ["game"]},
    )
    mock_filter(aioclient_mock, [make_giveaway(1)])
    await setup_entry(hass, mock_config_entry)
    await setup_entry(hass, other)

    mock_filter(aioclient_mock, [make_giveaway(1)])
    await hass.services.async_call(DOMAIN, "refresh", {}, blocking=True)
    assert aioclient_mock.call_count == 2


async def test_reset_seen_reports_everything_as_new(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """After a reset every current giveaway is announced again."""
    mock_filter(aioclient_mock, [make_giveaway(1), make_giveaway(2)])
    await setup_entry(hass, mock_config_entry)
    events = async_capture_events(hass, EVENT_NEW_GIVEAWAY)

    await hass.services.async_call(
        DOMAIN, "reset_seen", {ATTR_CONFIG_ENTRY_ID: ENTRY_ID}, blocking=True
    )
    await hass.async_block_till_done()
    assert sorted(event.data["id"] for event in events) == [1, 2]


@pytest.mark.parametrize("service", ["refresh", "get_giveaways", "reset_seen"])
async def test_invalid_entry(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    service: str,
) -> None:
    """Unknown and unloaded entries are rejected."""
    mock_filter(aioclient_mock, [make_giveaway(1)])
    await setup_entry(hass, mock_config_entry)
    kwargs = {"return_response": True} if service == "get_giveaways" else {}

    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, service, {ATTR_CONFIG_ENTRY_ID: "nope"}, blocking=True, **kwargs
        )
    assert err.value.translation_key == "entry_not_found"

    await hass.config_entries.async_unload(ENTRY_ID)
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, service, {ATTR_CONFIG_ENTRY_ID: ENTRY_ID}, blocking=True, **kwargs
        )
    assert err.value.translation_key == "entry_not_loaded"

    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(DOMAIN, service, {}, blocking=True, **kwargs)
    assert err.value.translation_key == "no_loaded_entries"


async def test_diagnostics(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Diagnostics describe the entry and the current data."""
    mock_filter(aioclient_mock, [make_giveaway(1), make_giveaway(2)])
    await setup_entry(hass, mock_config_entry)
    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry)
    assert diagnostics["entry"]["data"] == {
        CONF_PLATFORMS: ["steam", "epic-games-store"],
        CONF_TYPES: ["game"],
    }
    assert diagnostics["coordinator"]["last_update_success"] is True
    assert diagnostics["coordinator"]["seen_ids"] == 2
    assert diagnostics["data"]["filtered_count"] == 2
    assert [g["id"] for g in diagnostics["data"]["giveaways"]] == [1, 2]


async def test_remove_entry_deletes_store(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    hass_storage: dict,
) -> None:
    """Removing the entry deletes its seen IDs."""
    mock_filter(aioclient_mock, [make_giveaway(1)])
    await setup_entry(hass, mock_config_entry)
    assert f"{DOMAIN}.{ENTRY_ID}" in hass_storage
    await hass.config_entries.async_remove(ENTRY_ID)
    await hass.async_block_till_done()
    assert f"{DOMAIN}.{ENTRY_ID}" not in hass_storage
