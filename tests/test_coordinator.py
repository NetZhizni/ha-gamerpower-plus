"""Tests for updates, local filters and new-giveaway detection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp
from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.gamerpower_plus.api import Giveaway
from custom_components.gamerpower_plus.const import (
    CONF_EXCLUDE_KEYWORDS,
    CONF_INCLUDE_NO_WORTH,
    CONF_MIN_WORTH,
    CONF_SORT_BY,
    EVENT_NEW_GIVEAWAY,
    STORAGE_VERSION,
    storage_key,
)
from custom_components.gamerpower_plus.coordinator import (
    LocalFilters,
    apply_local_filters,
    parse_keywords,
    sort_giveaways,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, STATE_UNAVAILABLE
from homeassistant.core import CoreState, HomeAssistant

from .conftest import ENTRY_ID, get_entity_id, make_giveaway, mock_filter, setup_entry

STORE_KEY = storage_key(ENTRY_ID)


def stored_seen(hass_storage: dict[str, Any]) -> dict[str, str]:
    """Return the seen IDs written to the Store."""
    return hass_storage[STORE_KEY]["data"]


async def refresh(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Run a coordinator update."""
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


async def test_setup_and_unload(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The entry loads, creates its entities and unloads."""
    mock_filter(aioclient_mock, [make_giveaway(1), make_giveaway(2, worth="$5.01")])
    await setup_entry(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    assert (
        hass.states.get(get_entity_id(hass, "sensor", "active_giveaways")).state == "2"
    )
    assert hass.states.get(get_entity_id(hass, "sensor", "total_worth")).state == "15.0"

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retries_when_api_down(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """A failing first update puts the entry in setup retry."""
    mock_filter(aioclient_mock, exc=aiohttp.ClientConnectionError())
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_status_201_gives_zero(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """No active giveaways (HTTP 201) is a valid, empty state."""
    mock_filter(aioclient_mock, status=201)
    await setup_entry(hass, mock_config_entry)
    assert (
        hass.states.get(get_entity_id(hass, "sensor", "active_giveaways")).state == "0"
    )
    assert hass.states.get(get_entity_id(hass, "sensor", "total_worth")).state == "0.0"
    assert (
        hass.states.get(get_entity_id(hass, "sensor", "latest_giveaway")).state
        == "unknown"
    )
    assert (
        hass.states.get(get_entity_id(hass, "binary_sensor", "expiring_soon")).state
        == "off"
    )


@pytest.mark.parametrize(
    "failure",
    [
        {"exc": aiohttp.ClientConnectionError()},
        {"exc": TimeoutError()},
        {"status": 503},
        {"status": 200, "text": "not json"},
    ],
)
async def test_errors_make_entities_unavailable(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    failure: dict[str, Any],
) -> None:
    """Failures make entities unavailable instead of reporting 0."""
    mock_filter(aioclient_mock, [make_giveaway(1)])
    await setup_entry(hass, mock_config_entry)

    mock_filter(aioclient_mock, **failure)
    await refresh(hass, mock_config_entry)
    for platform, key in (
        ("sensor", "active_giveaways"),
        ("sensor", "total_worth"),
        ("sensor", "latest_giveaway"),
        ("binary_sensor", "expiring_soon"),
        ("calendar", "giveaways"),
        ("event", "new_giveaway"),
    ):
        assert (
            hass.states.get(get_entity_id(hass, platform, key)).state
            == STATE_UNAVAILABLE
        )

    mock_filter(aioclient_mock, [make_giveaway(1)])
    await refresh(hass, mock_config_entry)
    assert (
        hass.states.get(get_entity_id(hass, "sensor", "active_giveaways")).state == "1"
    )


async def test_scheduled_update(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """The coordinator polls with the configured interval."""
    mock_filter(aioclient_mock, [make_giveaway(1)])
    await setup_entry(hass, mock_config_entry)
    mock_filter(aioclient_mock, [make_giveaway(1), make_giveaway(2)])
    freezer.tick(timedelta(minutes=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert (
        hass.states.get(get_entity_id(hass, "sensor", "active_giveaways")).state == "2"
    )


@pytest.mark.parametrize(
    ("options", "expected_ids", "expected_worth"),
    [
        ({CONF_MIN_WORTH: 10.0}, [2, 3], 25.0),
        ({CONF_MIN_WORTH: 10.0, CONF_INCLUDE_NO_WORTH: False}, [2], 25.0),
        ({CONF_INCLUDE_NO_WORTH: False}, [1, 2], 29.99),
        ({CONF_EXCLUDE_KEYWORDS: "PLAYTEST, dlc"}, [1], 4.99),
    ],
)
async def test_local_filters(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    options: dict[str, Any],
    expected_ids: list[int],
    expected_worth: float,
) -> None:
    """Worth, N/A and keyword filters apply, total worth follows the list."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry, options={**mock_config_entry.options, **options}
    )
    mock_filter(
        aioclient_mock,
        [
            make_giveaway(
                1, worth="$4.99", published=datetime(2026, 10, 3, tzinfo=UTC)
            ),
            make_giveaway(
                2,
                title="Big DLC Pack",
                worth="$25.00",
                published=datetime(2026, 10, 2, tzinfo=UTC),
            ),
            make_giveaway(
                3,
                title="Space Playtest",
                worth="N/A",
                published=datetime(2026, 10, 1, tzinfo=UTC),
            ),
        ],
    )
    await setup_entry(hass, mock_config_entry)
    data = mock_config_entry.runtime_data.data
    assert [g.id for g in data.giveaways] == expected_ids
    assert data.total_worth == expected_worth
    assert data.fetched_count == 3


async def test_sort_by_value(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The sort option is sent to the API and applied locally."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry, options={**mock_config_entry.options, CONF_SORT_BY: "value"}
    )
    mock_filter(
        aioclient_mock,
        [
            make_giveaway(1, worth="N/A"),
            make_giveaway(2, worth="$1.00"),
            make_giveaway(3, worth="$30.00"),
        ],
    )
    await setup_entry(hass, mock_config_entry)
    assert [g.id for g in mock_config_entry.runtime_data.data.giveaways] == [3, 2, 1]
    assert aioclient_mock.mock_calls[0][1].query["sort-by"] == "value"


def _giveaway(giveaway_id: int, **kwargs: Any) -> Giveaway:
    return Giveaway.from_api(make_giveaway(giveaway_id, **kwargs))


def test_filter_and_sort_helpers() -> None:
    """Helpers work without Home Assistant."""
    assert parse_keywords(" Demo, ,PLAYTEST ") == ("demo", "playtest")
    assert parse_keywords("") == ()
    items = [
        _giveaway(1, published=datetime(2026, 1, 1, tzinfo=UTC), worth="$3"),
        _giveaway(2, published=datetime(2026, 3, 1, tzinfo=UTC), worth="N/A"),
        _giveaway(3, published=datetime(2026, 2, 1, tzinfo=UTC), worth="$9"),
    ]
    assert [g.id for g in sort_giveaways(items, "date")] == [2, 3, 1]
    assert [g.id for g in sort_giveaways(items, "value")] == [3, 1, 2]
    assert [g.id for g in sort_giveaways(items, "popularity")] == [1, 2, 3]
    assert [g.id for g in apply_local_filters(items, LocalFilters(min_worth=5))] == [
        2,
        3,
    ]


async def test_first_run_records_baseline_without_events(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
) -> None:
    """With an empty Store everything is marked as seen and no event fires."""
    events = async_capture_events(hass, EVENT_NEW_GIVEAWAY)
    mock_filter(aioclient_mock, [make_giveaway(1), make_giveaway(2)])
    await setup_entry(hass, mock_config_entry)

    assert events == []
    assert set(stored_seen(hass_storage)) == {"1", "2"}
    assert (
        hass.states.get(get_entity_id(hass, "event", "new_giveaway")).state == "unknown"
    )


async def test_new_giveaway_fires_events(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
) -> None:
    """A new ID fires a bus event and triggers the event entity."""
    mock_filter(aioclient_mock, [make_giveaway(1)])
    await setup_entry(hass, mock_config_entry)
    events = async_capture_events(hass, EVENT_NEW_GIVEAWAY)

    end = datetime(2026, 10, 20, 23, 59, tzinfo=UTC)
    mock_filter(aioclient_mock, [make_giveaway(2, end=end), make_giveaway(1)])
    await refresh(hass, mock_config_entry)

    assert len(events) == 1
    data = events[0].data
    assert data["id"] == 2
    assert data["title"] == "Game 2 (Steam) Giveaway"
    assert data["worth"] == "$9.99"
    assert data["worth_value"] == 9.99
    assert data["platforms"] == ["PC", "Steam"]
    assert data["type"] == "Game"
    assert data["end_date"] == "2026-10-20T23:59:00+00:00"
    assert data["config_entry_id"] == ENTRY_ID
    assert data["entry_title"] == "Steam, Epic — game"
    assert set(data) == {
        "id",
        "title",
        "worth",
        "worth_value",
        "platforms",
        "type",
        "published_date",
        "end_date",
        "image",
        "thumbnail",
        "open_giveaway_url",
        "gamerpower_url",
        "description",
        "instructions",
        "config_entry_id",
        "entry_title",
    }

    state = hass.states.get(get_entity_id(hass, "event", "new_giveaway"))
    assert state.attributes["event_type"] == "new_giveaway"
    assert state.attributes["id"] == 2
    assert set(stored_seen(hass_storage)) == {"1", "2"}

    # The same response again fires nothing.
    await refresh(hass, mock_config_entry)
    assert len(events) == 1


async def test_reappearing_id_is_not_new(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """An ID that disappears for a while and comes back is not new."""
    mock_filter(aioclient_mock, [make_giveaway(1), make_giveaway(2)])
    await setup_entry(hass, mock_config_entry)
    events = async_capture_events(hass, EVENT_NEW_GIVEAWAY)

    mock_filter(aioclient_mock, [make_giveaway(1)])
    await refresh(hass, mock_config_entry)
    mock_filter(aioclient_mock, [make_giveaway(1), make_giveaway(2)])
    await refresh(hass, mock_config_entry)

    assert events == []


async def test_new_giveaway_filtered_out_locally(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
) -> None:
    """Hidden giveaways are remembered but not announced."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry, options={**mock_config_entry.options, CONF_MIN_WORTH: 10.0}
    )
    mock_filter(aioclient_mock, [make_giveaway(1, worth="$20")])
    await setup_entry(hass, mock_config_entry)
    events = async_capture_events(hass, EVENT_NEW_GIVEAWAY)

    mock_filter(
        aioclient_mock,
        [
            make_giveaway(1, worth="$20"),
            make_giveaway(2, worth="$1"),
            make_giveaway(3, worth="$15"),
        ],
    )
    await refresh(hass, mock_config_entry)

    assert [event.data["id"] for event in events] == [3]
    assert set(stored_seen(hass_storage)) == {"1", "2", "3"}


async def test_restart_detects_giveaways_from_downtime(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
) -> None:
    """Giveaways that appeared while HA was stopped are new after a restart."""
    hass_storage[STORE_KEY] = {
        "version": STORAGE_VERSION,
        "minor_version": 1,
        "key": STORE_KEY,
        "data": {"1": "2026-10-01T00:00:00+00:00"},
    }
    events = async_capture_events(hass, EVENT_NEW_GIVEAWAY)
    mock_filter(aioclient_mock, [make_giveaway(1), make_giveaway(2), make_giveaway(3)])
    await setup_entry(hass, mock_config_entry)

    assert sorted(event.data["id"] for event in events) == [2, 3]
    state = hass.states.get(get_entity_id(hass, "event", "new_giveaway"))
    assert state.attributes["event_type"] == "new_giveaway"


async def test_events_wait_until_started(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
) -> None:
    """Events found during startup are sent once Home Assistant has started."""
    hass_storage[STORE_KEY] = {
        "version": STORAGE_VERSION,
        "minor_version": 1,
        "key": STORE_KEY,
        "data": {},
    }
    hass.set_state(CoreState.not_running)
    events = async_capture_events(hass, EVENT_NEW_GIVEAWAY)
    mock_filter(aioclient_mock, [make_giveaway(1)])
    await setup_entry(hass, mock_config_entry)
    assert events == []

    hass.set_state(CoreState.running)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()
    assert [event.data["id"] for event in events] == [1]


async def test_seen_retention(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Old IDs are dropped only when they are no longer in the response."""
    freezer.move_to("2026-10-10 12:00:00+00:00")
    hass_storage[STORE_KEY] = {
        "version": STORAGE_VERSION,
        "minor_version": 1,
        "key": STORE_KEY,
        "data": {
            "1": "2026-07-01T00:00:00+00:00",  # old, still active
            "2": "2026-07-01T00:00:00+00:00",  # old, gone
            "3": "2026-10-01T00:00:00+00:00",  # recent, gone
            "4": "garbage",  # unreadable, gone
        },
    }
    mock_filter(aioclient_mock, [make_giveaway(1)])
    await setup_entry(hass, mock_config_entry)
    assert stored_seen(hass_storage) == {
        "1": "2026-07-01T00:00:00+00:00",
        "3": "2026-10-01T00:00:00+00:00",
    }
