"""Calendar for GamerPower Plus."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import Giveaway
from .coordinator import GamerPowerConfigEntry, GamerPowerCoordinator
from .entity import GamerPowerEntity

PARALLEL_UPDATES = 0

_MIN_DURATION = timedelta(minutes=1)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GamerPowerConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the calendar."""
    async_add_entities([GiveawayCalendar(entry.runtime_data)])


def giveaway_to_event(giveaway: Giveaway) -> CalendarEvent | None:
    """Return a calendar event spanning publication to end, if both are known."""
    if giveaway.published_date is None or giveaway.end_date is None:
        return None
    start = giveaway.published_date
    end = max(giveaway.end_date, start + _MIN_DURATION)
    lines = [giveaway.description.strip(), f"Worth: {giveaway.worth}"]
    if giveaway.open_giveaway_url:
        lines.append(giveaway.open_giveaway_url)
    return CalendarEvent(
        start=start,
        end=end,
        summary=giveaway.title,
        description="\n\n".join(line for line in lines if line),
        location=", ".join(giveaway.platforms) or None,
        uid=f"gamerpower-{giveaway.id}",
    )


class GiveawayCalendar(GamerPowerEntity, CalendarEntity):
    """Giveaways with a known end date as calendar events."""

    def __init__(self, coordinator: GamerPowerCoordinator) -> None:
        """Initialize the calendar."""
        super().__init__(coordinator, "giveaways")

    def _events(self) -> list[CalendarEvent]:
        return [
            event
            for g in self.coordinator.data.giveaways
            if (event := giveaway_to_event(g)) is not None
        ]

    @property
    def event(self) -> CalendarEvent | None:
        """Return the running giveaway that ends first, else the next one."""
        now = dt_util.utcnow()
        events = [e for e in self._events() if e.end_datetime_local > now]
        running = [e for e in events if e.start_datetime_local <= now]
        if running:
            return min(running, key=lambda e: e.end_datetime_local)
        return min(events, key=lambda e: e.start_datetime_local, default=None)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return the giveaways overlapping the requested range."""
        return [
            event
            for event in self._events()
            if event.start_datetime_local < end_date
            and event.end_datetime_local > start_date
        ]
