"""Data update coordinator for GamerPower Plus."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import GamerPowerClient, GamerPowerError, Giveaway
from .const import (
    CONF_EXCLUDE_KEYWORDS,
    CONF_EXPIRING_HOURS,
    CONF_INCLUDE_NO_WORTH,
    CONF_MIN_WORTH,
    CONF_PLATFORMS,
    CONF_SORT_BY,
    CONF_TYPES,
    CONF_UPDATE_INTERVAL,
    DEFAULT_EXPIRING_HOURS,
    DEFAULT_INCLUDE_NO_WORTH,
    DEFAULT_MIN_WORTH,
    DEFAULT_SORT_BY,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    EVENT_NEW_GIVEAWAY,
    MIN_UPDATE_INTERVAL,
    SEEN_RETENTION,
    SORT_DATE,
    SORT_VALUE,
    STORAGE_VERSION,
    signal_new_giveaway,
    storage_key,
)

_LOGGER = logging.getLogger(__name__)

type GamerPowerConfigEntry = ConfigEntry[GamerPowerCoordinator]

_OLDEST = datetime.min.replace(tzinfo=UTC)


def parse_keywords(value: str | Iterable[str] | None) -> tuple[str, ...]:
    """Turn a comma separated keyword string into lower-cased keywords."""
    if not value:
        return ()
    parts = value.split(",") if isinstance(value, str) else value
    return tuple(kw for part in parts if (kw := part.strip().casefold()))


@dataclass(frozen=True, slots=True, kw_only=True)
class LocalFilters:
    """Filters applied after the API response."""

    min_worth: float = DEFAULT_MIN_WORTH
    include_no_worth: bool = DEFAULT_INCLUDE_NO_WORTH
    exclude_keywords: tuple[str, ...] = ()

    @classmethod
    def from_options(cls, options: Mapping[str, Any]) -> LocalFilters:
        """Build the filters from config entry options."""
        return cls(
            min_worth=float(options.get(CONF_MIN_WORTH, DEFAULT_MIN_WORTH)),
            include_no_worth=bool(
                options.get(CONF_INCLUDE_NO_WORTH, DEFAULT_INCLUDE_NO_WORTH)
            ),
            exclude_keywords=parse_keywords(options.get(CONF_EXCLUDE_KEYWORDS)),
        )

    def matches(self, giveaway: Giveaway) -> bool:
        """Return True if the giveaway passes all local filters."""
        if giveaway.worth_value is None:
            if not self.include_no_worth:
                return False
        elif giveaway.worth_value < self.min_worth:
            return False
        title = giveaway.title.casefold()
        return not any(keyword in title for keyword in self.exclude_keywords)


def apply_local_filters(
    giveaways: Iterable[Giveaway], filters: LocalFilters
) -> list[Giveaway]:
    """Return the giveaways that pass the local filters, keeping order."""
    return [giveaway for giveaway in giveaways if filters.matches(giveaway)]


def sort_giveaways(giveaways: Iterable[Giveaway], sort_by: str) -> list[Giveaway]:
    """Sort locally so the order is stable after filtering.

    ``popularity`` keeps the API order: the API does not expose the metric it
    uses (it is not ``users``).
    """
    if sort_by == SORT_DATE:
        return sorted(
            giveaways, key=lambda g: g.published_date or _OLDEST, reverse=True
        )
    if sort_by == SORT_VALUE:
        return sorted(
            giveaways,
            key=lambda g: (g.worth_value is not None, g.worth_value or 0.0),
            reverse=True,
        )
    return list(giveaways)


def _parse_seen(value: Any) -> datetime | None:
    """Parse a stored first-seen timestamp; invalid values give None."""
    if not isinstance(value, str):
        return None
    try:
        parsed = dt_util.parse_datetime(value)
    except ValueError:
        return None
    if parsed is not None and parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def total_worth(giveaways: Iterable[Giveaway]) -> float:
    """Sum the known worth of the giveaways in USD."""
    return round(
        sum((g.worth_value for g in giveaways if g.worth_value is not None), 0.0), 2
    )


@dataclass(slots=True, kw_only=True)
class GamerPowerData:
    """Result of one coordinator update."""

    giveaways: list[Giveaway] = field(default_factory=list)
    total_worth: float = 0.0
    new_giveaways: list[Giveaway] = field(default_factory=list)
    fetched_count: int = 0

    @property
    def latest(self) -> Giveaway | None:
        """Return the most recently published giveaway."""
        if not self.giveaways:
            return None
        return max(self.giveaways, key=lambda g: g.published_date or _OLDEST)


class GamerPowerCoordinator(DataUpdateCoordinator[GamerPowerData]):
    """Fetch, filter and track giveaways for one config entry."""

    config_entry: GamerPowerConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: GamerPowerConfigEntry,
        client: GamerPowerClient,
    ) -> None:
        """Initialize the coordinator."""
        options = entry.options
        interval = max(
            int(options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)),
            MIN_UPDATE_INTERVAL,
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(minutes=interval),
        )
        self.client = client
        self.platforms: list[str] = list(entry.data[CONF_PLATFORMS])
        self.types: list[str] = list(entry.data[CONF_TYPES])
        self.sort_by: str = options.get(CONF_SORT_BY, DEFAULT_SORT_BY)
        self.filters = LocalFilters.from_options(options)
        self.expiring_threshold = timedelta(
            hours=float(options.get(CONF_EXPIRING_HOURS, DEFAULT_EXPIRING_HOURS))
        )
        self._store: Store[dict[str, str]] = Store(
            hass, STORAGE_VERSION, storage_key(entry.entry_id)
        )
        # None until something was stored: the first run only records a baseline.
        self._seen: dict[str, str] | None = None
        self._pending_new: list[Giveaway] = []
        self._dispatch_enabled = False

    @property
    def seen_count(self) -> int:
        """Return how many giveaway IDs are remembered."""
        return len(self._seen or {})

    async def _async_setup(self) -> None:
        """Load the IDs seen before the last restart."""
        stored = await self._store.async_load()
        self._seen = dict(stored) if isinstance(stored, Mapping) else None

    async def _async_update_data(self) -> GamerPowerData:
        """Fetch giveaways, apply local filters and detect new ones."""
        try:
            fetched = await self.client.async_get_giveaways(
                self.platforms, self.types, self.sort_by
            )
        except GamerPowerError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err

        giveaways = sort_giveaways(
            apply_local_filters(fetched, self.filters), self.sort_by
        )
        # Seen IDs follow the raw API answer, so changing local filters later
        # never turns old giveaways into "new" ones.
        new_ids = await self._async_track_seen(fetched)
        new_giveaways = [g for g in giveaways if g.id in new_ids]
        self._pending_new.extend(new_giveaways)

        return GamerPowerData(
            giveaways=giveaways,
            total_worth=total_worth(giveaways),
            new_giveaways=new_giveaways,
            fetched_count=len(fetched),
        )

    async def _async_track_seen(self, fetched: list[Giveaway]) -> set[int]:
        """Update the seen IDs and return the IDs that were not seen before."""
        now = dt_util.utcnow()
        first_run = self._seen is None
        previous = self._seen or {}
        seen = dict(previous)
        current_ids = {str(g.id) for g in fetched}

        new_ids = {g.id for g in fetched if str(g.id) not in previous}
        for giveaway_id in new_ids:
            seen[str(giveaway_id)] = now.isoformat()

        # Forget IDs that left the response and are older than the retention.
        cutoff = now - SEEN_RETENTION
        for giveaway_id, first_seen in list(seen.items()):
            if giveaway_id in current_ids:
                continue
            seen_at = _parse_seen(first_seen)
            if seen_at is None or seen_at < cutoff:
                del seen[giveaway_id]

        if first_run or seen != previous:
            self._seen = seen
            await self._store.async_save(seen)

        if first_run:
            _LOGGER.debug(
                "%s: first run, recorded %d giveaways without events",
                self.config_entry.title,
                len(seen),
            )
            return set()
        return new_ids

    async def async_reset_seen(self) -> None:
        """Forget all seen IDs; the next update reports every giveaway as new."""
        self._seen = {}
        await self._store.async_save({})
        await self.async_refresh()

    @callback
    def async_update_listeners(self) -> None:
        """Update entities first, then announce new giveaways."""
        super().async_update_listeners()
        self._async_dispatch_new()

    @callback
    def async_enable_new_giveaway_dispatch(self) -> CALLBACK_TYPE:
        """Start announcing new giveaways once Home Assistant has started.

        Automations attach their triggers on ``homeassistant_started``; events
        found while starting (giveaways published during downtime) are queued
        until then instead of being lost.
        """

        @callback
        def _started(_hass: HomeAssistant) -> None:
            self._dispatch_enabled = True
            self._async_dispatch_new()

        return async_at_started(self.hass, _started)

    @callback
    def _async_dispatch_new(self) -> None:
        if not self._dispatch_enabled or not self._pending_new:
            return
        pending, self._pending_new = self._pending_new, []
        signal = signal_new_giveaway(self.config_entry.entry_id)
        for giveaway in pending:
            payload = self.event_payload(giveaway)
            _LOGGER.debug("New giveaway: %s", giveaway.title)
            self.hass.bus.async_fire(EVENT_NEW_GIVEAWAY, payload)
            async_dispatcher_send(self.hass, signal, payload)

    def event_payload(self, giveaway: Giveaway) -> dict[str, Any]:
        """Return the data sent with a new giveaway event."""
        data = giveaway.as_dict()
        return {
            "id": data["id"],
            "title": data["title"],
            "worth": data["worth"],
            "worth_value": data["worth_value"],
            "platforms": data["platforms"],
            "type": data["type"],
            "published_date": data["published_date"],
            "end_date": data["end_date"],
            "image": data["image"],
            "thumbnail": data["thumbnail"],
            "open_giveaway_url": data["open_giveaway_url"],
            "gamerpower_url": data["gamerpower_url"],
            "description": data["description"],
            "instructions": data["instructions"],
            "config_entry_id": self.config_entry.entry_id,
            "entry_title": self.config_entry.title,
        }


async def async_remove_seen_store(hass: HomeAssistant, entry_id: str) -> None:
    """Delete the stored seen IDs of an entry."""
    await Store[dict[str, str]](
        hass, STORAGE_VERSION, storage_key(entry_id)
    ).async_remove()
