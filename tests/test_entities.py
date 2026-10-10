"""Tests for the GamerPower Plus entities."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.gamerpower_plus.const import (
    ATTRIBUTION,
    CONF_EXPIRING_HOURS,
    DOMAIN,
    MAX_ATTRIBUTES_BYTES,
)
from homeassistant.const import ATTR_ATTRIBUTION, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.json import json_bytes
from homeassistant.util import dt as dt_util

from .conftest import ENTRY_ID, get_entity_id, make_giveaway, mock_filter, setup_entry


async def test_sensor_states_and_attributes(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Sensors expose count, worth and the latest giveaway."""
    now = dt_util.utcnow()
    mock_filter(
        aioclient_mock,
        [
            make_giveaway(1, worth="$10.00", published=now - timedelta(days=2)),
            make_giveaway(
                2, title="Newest", worth="N/A", published=now - timedelta(hours=1)
            ),
            make_giveaway(3, worth="$5.50", published=now - timedelta(days=1)),
        ],
    )
    await setup_entry(hass, mock_config_entry)

    active = hass.states.get(get_entity_id(hass, "sensor", "active_giveaways"))
    assert active.state == "3"
    assert active.attributes[ATTR_ATTRIBUTION] == ATTRIBUTION
    assert active.attributes["truncated"] is False
    assert active.attributes["giveaways"][0] == {
        "id": 2,
        "title": "Newest",
        "worth": "N/A",
        "end_date": None,
        "url": "https://www.gamerpower.com/open/giveaway-2",
        "image": "https://www.gamerpower.com/offers/1b/giveaway-2.jpg",
    }

    worth = hass.states.get(get_entity_id(hass, "sensor", "total_worth"))
    assert worth.state == "15.5"
    assert worth.attributes["unit_of_measurement"] == "USD"
    assert worth.attributes["device_class"] == "monetary"
    assert worth.attributes["state_class"] == "total"
    assert worth.attributes["giveaways_without_worth"] == 1

    latest = hass.states.get(get_entity_id(hass, "sensor", "latest_giveaway"))
    assert latest.state == "Newest"
    assert latest.attributes["id"] == 2
    assert latest.attributes["description"] == "Description of 2"
    assert latest.attributes["entity_picture"].endswith("giveaway-2.jpg")

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, ENTRY_ID), ENTRY_ID
    )
    assert device is not None
    assert device.name == "Steam, Epic — game"
    assert device.entry_type is dr.DeviceEntryType.SERVICE


async def test_list_attribute_is_limited(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Large lists are cut so the attributes stay below 16 KB."""
    mock_filter(
        aioclient_mock,
        [
            make_giveaway(i, title=f"{'Very long title ' * 8} {i}")
            for i in range(1, 301)
        ],
    )
    await setup_entry(hass, mock_config_entry)
    state = hass.states.get(get_entity_id(hass, "sensor", "active_giveaways"))
    assert state.state == "300"
    assert state.attributes["truncated"] is True
    assert 0 < len(state.attributes["giveaways"]) < 300
    assert len(json_bytes(dict(state.attributes))) < MAX_ATTRIBUTES_BYTES


async def test_expiring_soon(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The binary sensor follows giveaways entering the window and expiring."""
    assert mock_config_entry.options[CONF_EXPIRING_HOURS] == 24
    freezer.move_to("2026-10-10 12:00:00+00:00")
    now = dt_util.utcnow()
    mock_filter(
        aioclient_mock,
        [
            make_giveaway(1, end=now + timedelta(hours=2)),
            make_giveaway(2, end=now + timedelta(hours=30)),
            make_giveaway(3),
        ],
    )
    await setup_entry(hass, mock_config_entry)
    entity_id = get_entity_id(hass, "binary_sensor", "expiring_soon")

    state = hass.states.get(entity_id)
    assert state.state == "on"
    assert [g["id"] for g in state.attributes["giveaways"]] == [1]
    assert state.attributes["threshold_hours"] == 24

    # Giveaway 1 expires: nothing ends within 24 hours any more.
    freezer.tick(timedelta(hours=2, seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "off"

    # Giveaway 2 enters the window without a coordinator update.
    freezer.tick(timedelta(hours=4))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.state == "on"
    assert [g["id"] for g in state.attributes["giveaways"]] == [2]


async def test_calendar(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Giveaways with an end date are calendar events."""
    freezer.move_to("2026-10-10 12:00:00+00:00")
    now = dt_util.utcnow()
    mock_filter(
        aioclient_mock,
        [
            make_giveaway(
                1,
                title="Ends later",
                published=now - timedelta(days=1),
                end=now + timedelta(days=5),
            ),
            make_giveaway(
                2,
                title="Ends first",
                published=now - timedelta(days=2),
                end=now + timedelta(days=1),
            ),
            make_giveaway(3, title="No end", published=now - timedelta(days=1)),
        ],
    )
    await setup_entry(hass, mock_config_entry)
    entity_id = get_entity_id(hass, "calendar", "giveaways")

    state = hass.states.get(entity_id)
    assert state.state == "on"
    assert state.attributes["message"] == "Ends first"

    response = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            ATTR_ENTITY_ID: entity_id,
            "start_date_time": now,
            "end_date_time": now + timedelta(days=30),
        },
        blocking=True,
        return_response=True,
    )
    events = response[entity_id]["events"]
    assert sorted(e["summary"] for e in events) == ["Ends first", "Ends later"]
    event = next(e for e in events if e["summary"] == "Ends first")
    assert "https://www.gamerpower.com/open/giveaway-2" in event["description"]
    assert "Worth: $9.99" in event["description"]
    assert event["location"] == "PC, Steam"
