"""Tests for the GamerPower API client."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import time

import aiohttp
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.gamerpower_plus.api import (
    GamerPowerConnectionError,
    GamerPowerResponseError,
    Giveaway,
    RequestThrottle,
    async_create_client,
    build_user_agent,
    parse_datetime,
    parse_giveaways,
    parse_platforms,
    parse_worth,
)
from custom_components.gamerpower_plus.const import DOMAIN
from homeassistant.core import HomeAssistant

from .conftest import load_fixture_json, mock_filter

MANIFEST = Path(__file__).parents[1] / "custom_components" / DOMAIN / "manifest.json"

# Captured at import time, before the autouse fixture patches it out.
_REAL_THROTTLE_WAIT = RequestThrottle.wait


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("$19.99", 19.99),
        ("$1,299.00", 1299.0),
        (" $0.00 ", 0.0),
        ("N/A", None),
        ("n/a", None),
        ("", None),
        ("free", None),
        (None, None),
        (True, None),
        (4, 4.0),
    ],
)
def test_parse_worth(value: object, expected: float | None) -> None:
    """Worth strings become floats, unknown values None."""
    assert parse_worth(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-10-12 23:59:00", datetime(2026, 10, 12, 23, 59, tzinfo=UTC)),
        ("2026-10-12T23:59:00+02:00", datetime(2026, 10, 12, 21, 59, tzinfo=UTC)),
        ("N/A", None),
        ("", None),
        ("0000-00-00 00:00:00", None),
        (None, None),
    ],
)
def test_parse_datetime(value: object, expected: datetime | None) -> None:
    """Dates are parsed as aware datetimes."""
    parsed = parse_datetime(value)
    assert parsed == expected
    if parsed is not None:
        assert parsed.tzinfo is not None


def test_parse_platforms() -> None:
    """Platforms are split on commas."""
    assert parse_platforms("PC, Steam, Epic Games Store") == [
        "PC",
        "Steam",
        "Epic Games Store",
    ]
    assert parse_platforms("") == []
    assert parse_platforms(None) == []


def test_parse_real_response() -> None:
    """A real API response (2026-10-10) is parsed completely."""
    giveaways = parse_giveaways(load_fixture_json("giveaways.json"))
    assert len(giveaways) == 5
    first = giveaways[0]
    assert first.id == 3810
    assert first.worth == "$7.99"
    assert first.worth_value == 7.99
    assert first.platforms == ["PC", "Steam"]
    assert first.end_date == datetime(2026, 10, 12, 23, 59, tzinfo=UTC)
    assert first.published_date == datetime(2026, 10, 9, 13, 15, 36, tzinfo=UTC)
    assert first.open_giveaway_url.startswith("https://www.gamerpower.com/open/")
    no_worth = next(g for g in giveaways if g.id == 3803)
    assert no_worth.worth == "N/A"
    assert no_worth.worth_value is None
    assert no_worth.end_date is None
    assert first.as_dict()["end_date"] == "2026-10-12T23:59:00+00:00"


def test_parse_skips_malformed_items() -> None:
    """Items without a usable id are skipped."""
    giveaways = parse_giveaways(
        [{"title": "no id"}, "junk", {"id": "12", "title": "ok"}]
    )
    assert [g.id for g in giveaways] == [12]
    with pytest.raises(GamerPowerResponseError):
        parse_giveaways({"status": 0})
    with pytest.raises(ValueError, match="Invalid giveaway id"):
        Giveaway.from_api({"id": None})


async def test_request_parameters(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Platforms and types are joined with dots, sort-by is passed on."""
    mock_filter(aioclient_mock, load_fixture_json("giveaways.json"))
    client = await async_create_client(hass)
    giveaways = await client.async_get_giveaways(
        ["steam", "epic-games-store"], ["game", "loot"], "value"
    )
    assert len(giveaways) == 5
    _, url, _, headers = aioclient_mock.mock_calls[0]
    assert url.query["platform"] == "steam.epic-games-store"
    assert url.query["type"] == "game.loot"
    assert url.query["sort-by"] == "value"
    version = json.loads(MANIFEST.read_text("utf-8"))["version"]
    assert f"ha-gamerpower-plus/{version} " in headers["User-Agent"]


@pytest.mark.parametrize(
    ("platforms", "types"),
    [(["foo"], ["game"]), (["steam"], ["foo"]), ([], ["game"]), (["steam"], [])],
)
async def test_unknown_filters_rejected(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    platforms: list[str],
    types: list[str],
) -> None:
    """Unknown values are not sent; /filter would ignore them and widen results."""
    client = await async_create_client(hass)
    with pytest.raises(ValueError, match="Unsupported"):
        await client.async_get_giveaways(platforms, types)
    assert aioclient_mock.call_count == 0


async def test_status_201_is_empty(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """HTTP 201 means no active giveaways, not an error."""
    mock_filter(aioclient_mock, status=201)
    client = await async_create_client(hass)
    assert await client.async_get_giveaways(["gog"], ["beta"]) == []


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"status": 500}, GamerPowerResponseError),
        ({"status": 404}, GamerPowerResponseError),
        ({"status": 200, "text": "<html>maintenance</html>"}, GamerPowerResponseError),
        ({"exc": aiohttp.ClientConnectionError()}, GamerPowerConnectionError),
        ({"exc": TimeoutError()}, GamerPowerConnectionError),
    ],
)
async def test_request_errors(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    kwargs: dict,
    error: type[Exception],
) -> None:
    """Network errors, bad statuses and invalid JSON raise errors."""
    mock_filter(aioclient_mock, **kwargs)
    client = await async_create_client(hass)
    with pytest.raises(error):
        await client.async_get_giveaways(["steam"], ["game"])


async def test_other_endpoints(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """/giveaways, /giveaway and /worth are parsed."""
    raw = load_fixture_json("giveaways.json")
    aioclient_mock.get("https://www.gamerpower.com/api/giveaways", json=raw)
    aioclient_mock.get("https://www.gamerpower.com/api/giveaway", json=raw[0])
    aioclient_mock.get(
        "https://www.gamerpower.com/api/worth",
        json={"active_giveaways_number": 33, "worth_estimation_usd": "133.88"},
    )
    client = await async_create_client(hass)
    assert len(await client.async_get_all_giveaways("steam", "game", "date")) == 5
    giveaway = await client.async_get_giveaway(3810)
    assert giveaway is not None
    assert giveaway.id == 3810
    assert await client.async_get_worth("steam") == (33, 133.88)


async def test_throttle_spaces_requests() -> None:
    """Consecutive requests wait for the minimum interval."""
    throttle = RequestThrottle(min_interval=0.05)
    start = time.monotonic()
    for _ in range(3):
        await _REAL_THROTTLE_WAIT(throttle)
    assert time.monotonic() - start >= 0.1


async def test_client_shares_throttle(hass: HomeAssistant) -> None:
    """All clients of one hass instance share the throttle."""
    first, second = await async_create_client(hass), await async_create_client(hass)
    assert first._throttle is second._throttle


def test_user_agent_without_version() -> None:
    """A client created without a version still identifies the integration."""
    assert "ha-gamerpower-plus (+" in build_user_agent()
