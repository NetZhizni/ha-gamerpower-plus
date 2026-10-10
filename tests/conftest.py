"""Fixtures for GamerPower Plus tests."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.gamerpower_plus.const import (
    CONF_PLATFORMS,
    CONF_TYPES,
    DEFAULT_OPTIONS,
    DOMAIN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

FILTER_URL = "https://www.gamerpower.com/api/filter"
ENTRY_ID = "01TESTENTRY"
FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture_json(name: str) -> Any:
    """Load a JSON fixture."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def api_date(value: datetime | None) -> str:
    """Format a datetime the way the API does."""
    if value is None:
        return "N/A"
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


def make_giveaway(
    giveaway_id: int,
    *,
    title: str | None = None,
    worth: str = "$9.99",
    published: datetime | None = None,
    end: datetime | None = None,
    platforms: str = "PC, Steam",
    giveaway_type: str = "Game",
) -> dict[str, Any]:
    """Return a raw API giveaway object."""
    published = published or datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    slug = f"giveaway-{giveaway_id}"
    return {
        "id": giveaway_id,
        "title": title or f"Game {giveaway_id} (Steam) Giveaway",
        "worth": worth,
        "thumbnail": f"https://www.gamerpower.com/offers/1/{slug}.jpg",
        "image": f"https://www.gamerpower.com/offers/1b/{slug}.jpg",
        "description": f"Description of {giveaway_id}",
        "instructions": "1. Click the button.\r\n2. Have fun!",
        "open_giveaway_url": f"https://www.gamerpower.com/open/{slug}",
        "published_date": api_date(published),
        "type": giveaway_type,
        "platforms": platforms,
        "end_date": api_date(end),
        "users": 1000 + giveaway_id,
        "status": "Active",
        "gamerpower_url": f"https://www.gamerpower.com/{slug}",
        "open_giveaway": f"https://www.gamerpower.com/open/{slug}",
    }


def mock_filter(
    aioclient_mock: AiohttpClientMocker,
    giveaways: list[dict[str, Any]] | None = None,
    *,
    status: int = 200,
    exc: Exception | None = None,
    text: str | None = None,
) -> None:
    """Replace the mocked /filter response."""
    aioclient_mock.clear_requests()
    if exc is not None:
        aioclient_mock.get(FILTER_URL, exc=exc)
    elif text is not None:
        aioclient_mock.get(FILTER_URL, status=status, text=text)
    elif status == 201:
        aioclient_mock.get(
            FILTER_URL,
            status=201,
            json={"status": 0, "status_message": "No active giveaways available"},
        )
    else:
        aioclient_mock.get(FILTER_URL, status=status, json=giveaways or [])


def get_entity_id(hass: HomeAssistant, platform: str, key: str) -> str:
    """Return the entity ID of an entity of the test entry."""
    entity_id = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{ENTRY_ID}_{key}"
    )
    assert entity_id is not None
    return entity_id


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations in all tests."""


@pytest.fixture(autouse=True)
def no_throttle() -> Generator[None]:
    """Skip request spacing; it is tested separately."""
    with patch(
        "custom_components.gamerpower_plus.api.RequestThrottle.wait",
        return_value=None,
    ):
        yield


@pytest.fixture
def options() -> dict[str, Any]:
    """Return the entry options; override to change them."""
    return dict(DEFAULT_OPTIONS)


@pytest.fixture
def mock_config_entry(options: dict[str, Any]) -> MockConfigEntry:
    """Return a config entry for Steam and Epic games."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Steam, Epic — game",
        unique_id="epic-games-store.steam|game",
        entry_id=ENTRY_ID,
        data={CONF_PLATFORMS: ["steam", "epic-games-store"], CONF_TYPES: ["game"]},
        options=options,
    )


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Add and set up a config entry."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
