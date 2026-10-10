"""Tests for the GamerPower Plus config, options and reconfigure flows."""

from __future__ import annotations

from datetime import timedelta

import aiohttp
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.gamerpower_plus.const import (
    CONF_EXCLUDE_KEYWORDS,
    CONF_EXPIRING_HOURS,
    CONF_INCLUDE_NO_WORTH,
    CONF_MIN_WORTH,
    CONF_PLATFORMS,
    CONF_SORT_BY,
    CONF_TYPES,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
    EVENT_NEW_GIVEAWAY,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import make_giveaway, mock_filter, setup_entry

USER_INPUT = {
    CONF_PLATFORMS: ["epic-games-store", "steam"],
    CONF_TYPES: ["game"],
    CONF_SORT_BY: "value",
    CONF_UPDATE_INTERVAL: 30,
    CONF_MIN_WORTH: 5,
    CONF_INCLUDE_NO_WORTH: False,
    CONF_EXCLUDE_KEYWORDS: " Demo ,  , Playtest",
    CONF_EXPIRING_HOURS: 12,
}


async def test_user_flow_success(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A valid form creates an entry with a generated title."""
    mock_filter(aioclient_mock, [make_giveaway(1)])
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Steam, Epic — game"
    assert result["data"] == {
        CONF_PLATFORMS: ["steam", "epic-games-store"],
        CONF_TYPES: ["game"],
    }
    assert result["options"] == {
        CONF_SORT_BY: "value",
        CONF_UPDATE_INTERVAL: 30,
        CONF_MIN_WORTH: 5.0,
        CONF_INCLUDE_NO_WORTH: False,
        CONF_EXCLUDE_KEYWORDS: "demo, playtest",
        CONF_EXPIRING_HOURS: 12,
    }
    assert result["result"].unique_id == "epic-games-store.steam|game"


async def test_user_flow_custom_name(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A given name is used as the title."""
    mock_filter(aioclient_mock, status=201)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, CONF_NAME: "  Free games  "}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Free games"


async def test_user_flow_duplicate(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The same platforms and types in another order are rejected."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, CONF_PLATFORMS: ["steam", "epic-games-store"]}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert aioclient_mock.call_count == 0


async def test_user_flow_cannot_connect_then_recovers(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A connection error shows an error; the next attempt succeeds."""
    mock_filter(aioclient_mock, exc=aiohttp.ClientConnectionError())
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    mock_filter(aioclient_mock, [make_giveaway(1)])
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_server_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """HTTP 5xx is reported as cannot_connect."""
    mock_filter(aioclient_mock, status=500)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_requires_selection(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Empty platform or type selections are rejected."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, CONF_PLATFORMS: [], CONF_TYPES: []}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {
        CONF_PLATFORMS: "no_platforms",
        CONF_TYPES: "no_types",
    }
    assert aioclient_mock.call_count == 0


async def test_options_flow_reloads(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Saving options updates the entry and reloads it."""
    mock_filter(
        aioclient_mock,
        [make_giveaway(1, worth="$2.00"), make_giveaway(2, worth="$20.00")],
    )
    await setup_entry(hass, mock_config_entry)
    old_coordinator = mock_config_entry.runtime_data
    assert len(old_coordinator.data.giveaways) == 2

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SORT_BY: "date",
            CONF_UPDATE_INTERVAL: 120,
            CONF_MIN_WORTH: 10,
            CONF_INCLUDE_NO_WORTH: True,
            CONF_EXPIRING_HOURS: 48,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_MIN_WORTH] == 10.0
    assert mock_config_entry.options[CONF_EXCLUDE_KEYWORDS] == ""
    coordinator = mock_config_entry.runtime_data
    assert coordinator is not old_coordinator
    assert coordinator.update_interval == timedelta(minutes=120)
    assert [g.id for g in coordinator.data.giveaways] == [2]


async def test_reconfigure_flow(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Changing platforms updates unique ID and title without new-giveaway events."""
    mock_filter(aioclient_mock, [make_giveaway(1)])
    await setup_entry(hass, mock_config_entry)
    events = async_capture_events(hass, EVENT_NEW_GIVEAWAY)

    # The new selection returns giveaways that were never seen before.
    mock_filter(aioclient_mock, [make_giveaway(10), make_giveaway(11)])
    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_PLATFORMS: ["gog", "steam"], CONF_TYPES: ["beta", "game"]},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.unique_id == "gog.steam|beta.game"
    assert mock_config_entry.title == "Steam, GOG — game, beta"
    assert mock_config_entry.data[CONF_PLATFORMS] == ["steam", "gog"]
    assert len(mock_config_entry.runtime_data.data.giveaways) == 2
    assert events == []


async def test_reconfigure_flow_duplicate(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Reconfiguring to the selection of another entry is rejected."""
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="gog|game",
        data={CONF_PLATFORMS: ["gog"], CONF_TYPES: ["game"]},
    ).add_to_hass(hass)
    mock_filter(aioclient_mock, [make_giveaway(1)])
    await setup_entry(hass, mock_config_entry)

    result = await mock_config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PLATFORMS: ["gog"], CONF_TYPES: ["game"]}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert mock_config_entry.unique_id == "epic-games-store.steam|game"
