"""Async client for the GamerPower API (https://www.gamerpower.com/api-read).

Facts verified against live responses on 2026-10-10 (sample in tests/fixtures):

* A giveaway object has 16 keys, all values are strings except ``id`` and
  ``users`` (int)::

    id, title, worth ("$7.99" | "N/A"), thumbnail, image, description,
    instructions, open_giveaway_url, open_giveaway (same as open_giveaway_url),
    published_date ("YYYY-MM-DD HH:MM:SS"), end_date (same format | "N/A"),
    type ("Game" | "DLC" | "Early Access" | "Other"), platforms ("PC, Steam"),
    users, status ("Active"), gamerpower_url

* ``type`` query values map to: game -> "Game", loot -> "DLC",
  beta -> "Early Access".
* ``/filter`` honours ``sort-by`` (date | value | popularity); unknown sort
  values fall back to date order. ``/filter`` silently ignores unknown
  ``type`` values and, when a type is given, unknown platforms too: the result
  then covers more than was asked for. Only ``platform=<unknown>`` without a
  type gives HTTP 500; ``/giveaways`` answers 404. ``/filter`` without any
  parameter is 404. The client therefore rejects unknown values itself.
* ``/worth`` takes a single platform only (``steam.epic-games-store`` -> 404),
  answers 404 for several valid platforms (ps5, itchio, ubisoft, ...) and may
  return ``"worth_estimation_usd": null``. It can't reproduce a multi-platform
  selection, so the integration sums worth locally.
* HTTP 201 with ``{"status": 0, "status_message": "No active giveaways ..."}``
  means there are no active giveaways; it is not an error.
* Dates carry no timezone; they are interpreted as UTC.
* Responses are served with ``Cache-Control: max-age=600``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
import time
from typing import Any

import aiohttp

from homeassistant.const import __version__ as ha_version
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util
from homeassistant.util.hass_dict import HassKey

from .const import (
    API_BASE_URL,
    API_MIN_REQUEST_INTERVAL,
    API_TIMEOUT,
    DOMAIN,
    GAMING_PLATFORMS,
    GIVEAWAY_TYPES,
    PROJECT_URL,
    VERSION,
)

_LOGGER = logging.getLogger(__name__)

USER_AGENT = f"HomeAssistant/{ha_version} ha-gamerpower-plus/{VERSION} (+{PROJECT_URL})"
DATA_THROTTLE: HassKey[RequestThrottle] = HassKey(f"{DOMAIN}_throttle")

_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_NOT_AVAILABLE = "N/A"


class GamerPowerError(Exception):
    """Base error raised by the GamerPower client."""


class GamerPowerConnectionError(GamerPowerError):
    """The API could not be reached."""


class GamerPowerResponseError(GamerPowerError):
    """The API answered with an unexpected status or payload."""


def parse_worth(value: Any) -> float | None:
    """Parse a worth string like ``"$19.99"``; ``"N/A"`` gives ``None``."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if not isinstance(value, str):
        return None
    cleaned = value.strip().replace("$", "").replace(",", "")
    if not cleaned or cleaned.upper() == _NOT_AVAILABLE:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_datetime(value: Any) -> datetime | None:
    """Parse an API date (``"YYYY-MM-DD HH:MM:SS"`` in UTC or ``"N/A"``)."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or value.upper() == _NOT_AVAILABLE:
        return None
    try:
        parsed: datetime | None = datetime.strptime(value, _DATE_FORMAT)  # noqa: DTZ007
    except ValueError:
        try:
            parsed = dt_util.parse_datetime(value)
        except ValueError:  # well formatted but impossible, e.g. year 0
            return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def parse_platforms(value: Any) -> list[str]:
    """Split a comma separated platform string into a list."""
    if not isinstance(value, str):
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _as_str(value: Any) -> str:
    return value if isinstance(value, str) else ""


@dataclass(frozen=True, slots=True, kw_only=True)
class Giveaway:
    """A giveaway as returned by the API, with parsed fields."""

    id: int
    title: str
    worth: str
    worth_value: float | None
    type: str
    platforms: list[str] = field(default_factory=list)
    published_date: datetime | None = None
    end_date: datetime | None = None
    image: str = ""
    thumbnail: str = ""
    description: str = ""
    instructions: str = ""
    open_giveaway_url: str = ""
    gamerpower_url: str = ""
    users: int | None = None
    status: str = ""

    @classmethod
    def from_api(cls, raw: Mapping[str, Any]) -> Giveaway:
        """Build a giveaway from an API object; raises ValueError if invalid."""
        giveaway_id = raw.get("id")
        if isinstance(giveaway_id, bool) or not isinstance(giveaway_id, int | str):
            raise ValueError(f"Invalid giveaway id: {giveaway_id!r}")
        users = raw.get("users")
        return cls(
            id=int(giveaway_id),
            title=_as_str(raw.get("title")),
            worth=_as_str(raw.get("worth")) or _NOT_AVAILABLE,
            worth_value=parse_worth(raw.get("worth")),
            type=_as_str(raw.get("type")),
            platforms=parse_platforms(raw.get("platforms")),
            published_date=parse_datetime(raw.get("published_date")),
            end_date=parse_datetime(raw.get("end_date")),
            image=_as_str(raw.get("image")),
            thumbnail=_as_str(raw.get("thumbnail")),
            description=_as_str(raw.get("description")),
            instructions=_as_str(raw.get("instructions")),
            open_giveaway_url=_as_str(
                raw.get("open_giveaway_url") or raw.get("open_giveaway")
            ),
            gamerpower_url=_as_str(raw.get("gamerpower_url")),
            users=users
            if isinstance(users, int) and not isinstance(users, bool)
            else None,
            status=_as_str(raw.get("status")),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return all fields in a JSON serializable form."""
        return {
            "id": self.id,
            "title": self.title,
            "worth": self.worth,
            "worth_value": self.worth_value,
            "type": self.type,
            "platforms": list(self.platforms),
            "published_date": _isoformat(self.published_date),
            "end_date": _isoformat(self.end_date),
            "image": self.image,
            "thumbnail": self.thumbnail,
            "description": self.description,
            "instructions": self.instructions,
            "open_giveaway_url": self.open_giveaway_url,
            "gamerpower_url": self.gamerpower_url,
            "users": self.users,
            "status": self.status,
        }

    def as_compact_dict(self) -> dict[str, Any]:
        """Return the small subset used in list attributes."""
        return {
            "id": self.id,
            "title": self.title,
            "worth": self.worth,
            "end_date": _isoformat(self.end_date),
            "url": self.open_giveaway_url,
            "image": self.image,
        }


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def parse_giveaways(data: Any) -> list[Giveaway]:
    """Parse a list response, skipping malformed items."""
    if not isinstance(data, list):
        raise GamerPowerResponseError(
            f"Expected a list of giveaways, got {type(data).__name__}"
        )
    giveaways: list[Giveaway] = []
    for item in data:
        if not isinstance(item, Mapping):
            _LOGGER.debug("Skipping malformed giveaway: %r", item)
            continue
        try:
            giveaways.append(Giveaway.from_api(item))
        except ValueError as err:
            _LOGGER.debug("Skipping malformed giveaway: %s", err)
    return giveaways


class RequestThrottle:
    """Space requests out so all entries together stay under the rate limit."""

    def __init__(self, min_interval: float = API_MIN_REQUEST_INTERVAL) -> None:
        """Initialize the throttle."""
        self._min_interval = min_interval
        self._lock = asyncio.Lock()
        self._next_slot = 0.0

    async def wait(self) -> None:
        """Wait until the next request slot is free."""
        async with self._lock:
            now = time.monotonic()
            if (delay := self._next_slot - now) > 0:
                await asyncio.sleep(delay)
                now = time.monotonic()
            self._next_slot = now + self._min_interval


class GamerPowerClient:
    """Minimal async GamerPower API client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        throttle: RequestThrottle | None = None,
        base_url: str = API_BASE_URL,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._throttle = throttle or RequestThrottle()
        self._base_url = base_url.rstrip("/")

    async def async_get_giveaways(
        self,
        platforms: Iterable[str],
        types: Iterable[str],
        sort_by: str | None = None,
    ) -> list[Giveaway]:
        """Return active giveaways for any of the platforms and types (``/filter``).

        Raises ValueError for unknown values, which the API would silently
        ignore and answer with a wider selection.
        """
        platforms, types = list(platforms), list(types)
        invalid = [p for p in platforms if p not in GAMING_PLATFORMS] + [
            t for t in types if t not in GIVEAWAY_TYPES
        ]
        if invalid or not platforms or not types:
            raise ValueError(f"Unsupported platform or type filter: {invalid}")
        params = {"platform": ".".join(platforms), "type": ".".join(types)}
        if sort_by:
            params["sort-by"] = sort_by
        data = await self._async_request("filter", params)
        return [] if data is None else parse_giveaways(data)

    async def async_get_all_giveaways(
        self,
        platform: str | None = None,
        giveaway_type: str | None = None,
        sort_by: str | None = None,
    ) -> list[Giveaway]:
        """Return active giveaways for one platform and type (``/giveaways``)."""
        params: dict[str, str] = {}
        if platform:
            params["platform"] = platform
        if giveaway_type:
            params["type"] = giveaway_type
        if sort_by:
            params["sort-by"] = sort_by
        data = await self._async_request("giveaways", params)
        return [] if data is None else parse_giveaways(data)

    async def async_get_giveaway(self, giveaway_id: int) -> Giveaway | None:
        """Return a single giveaway (``/giveaway``)."""
        data = await self._async_request("giveaway", {"id": str(giveaway_id)})
        if data is None:
            return None
        if not isinstance(data, Mapping):
            raise GamerPowerResponseError("Expected a giveaway object")
        try:
            return Giveaway.from_api(data)
        except ValueError as err:
            raise GamerPowerResponseError(str(err)) from err

    async def async_get_worth(
        self, platform: str | None = None, giveaway_type: str | None = None
    ) -> tuple[int, float | None]:
        """Return (active count, worth in USD) for one platform (``/worth``)."""
        params: dict[str, str] = {}
        if platform:
            params["platform"] = platform
        if giveaway_type:
            params["type"] = giveaway_type
        data = await self._async_request("worth", params)
        if data is None:
            return 0, 0.0
        if not isinstance(data, Mapping):
            raise GamerPowerResponseError("Expected a worth object")
        count = data.get("active_giveaways_number")
        return (
            count if isinstance(count, int) else 0,
            parse_worth(data.get("worth_estimation_usd")),
        )

    async def _async_request(self, endpoint: str, params: Mapping[str, str]) -> Any:
        """Perform a GET request; return ``None`` for HTTP 201 (no giveaways)."""
        url = f"{self._base_url}/{endpoint}"
        await self._throttle.wait()
        try:
            async with self._session.get(
                url,
                params=dict(params),
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
            ) as response:
                if response.status == 201:
                    return None
                if response.status != 200:
                    raise GamerPowerResponseError(
                        f"Unexpected HTTP status {response.status} from /{endpoint}"
                    )
                try:
                    return await response.json(content_type=None)
                except ValueError as err:
                    raise GamerPowerResponseError(
                        f"Invalid JSON from /{endpoint}"
                    ) from err
        except TimeoutError as err:
            raise GamerPowerConnectionError(
                f"Timeout while requesting /{endpoint}"
            ) from err
        except aiohttp.ClientError as err:
            raise GamerPowerConnectionError(
                f"Error requesting /{endpoint}: {err}"
            ) from err


@callback
def async_create_client(hass: HomeAssistant) -> GamerPowerClient:
    """Create a client that shares the session and throttle of all entries."""
    if (throttle := hass.data.get(DATA_THROTTLE)) is None:
        throttle = hass.data[DATA_THROTTLE] = RequestThrottle()
    return GamerPowerClient(async_get_clientsession(hass), throttle)
