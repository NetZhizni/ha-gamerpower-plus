"""Constants for the GamerPower Plus integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "gamerpower_plus"
NAME: Final = "GamerPower Plus"
VERSION: Final = "1.0.1"

ATTRIBUTION: Final = "Data provided by GamerPower.com"
MANUFACTURER: Final = "GamerPower"
CONFIGURATION_URL: Final = "https://www.gamerpower.com/"
PROJECT_URL: Final = "https://github.com/NetZhizni/ha-gamerpower-plus"

API_BASE_URL: Final = "https://www.gamerpower.com/api"
API_TIMEOUT: Final = 10
# GamerPower allows at most 10 requests per second.
API_MIN_REQUEST_INTERVAL: Final = 0.11

CONF_PLATFORMS: Final = "platforms"
CONF_TYPES: Final = "types"
CONF_SORT_BY: Final = "sort_by"
CONF_UPDATE_INTERVAL: Final = "update_interval"
CONF_MIN_WORTH: Final = "min_worth"
CONF_INCLUDE_NO_WORTH: Final = "include_no_worth"
CONF_EXCLUDE_KEYWORDS: Final = "exclude_keywords"
CONF_EXPIRING_HOURS: Final = "expiring_hours"

# Every platform value accepted by the API (verified 2026-10-10), mapped to the
# short label used when generating entry titles. Order is the UI order.
GAMING_PLATFORMS: Final[dict[str, str]] = {
    "steam": "Steam",
    "epic-games-store": "Epic",
    "pc": "PC",
    "gog": "GOG",
    "ubisoft": "Ubisoft",
    "itchio": "itch.io",
    "battlenet": "Battle.net",
    "origin": "Origin",
    "drm-free": "DRM-Free",
    "ps4": "PS4",
    "ps5": "PS5",
    "xbox-one": "Xbox One",
    "xbox-series-xs": "Xbox Series X|S",
    "xbox-360": "Xbox 360",
    "switch": "Switch",
    "android": "Android",
    "ios": "iOS",
    "vr": "VR",
}
GIVEAWAY_TYPES: Final = ("game", "loot", "beta")

SORT_DATE: Final = "date"
SORT_VALUE: Final = "value"
SORT_POPULARITY: Final = "popularity"
SORT_OPTIONS: Final = (SORT_DATE, SORT_VALUE, SORT_POPULARITY)

DEFAULT_PLATFORMS: Final = ["steam", "epic-games-store"]
DEFAULT_TYPES: Final = ["game"]
DEFAULT_SORT_BY: Final = SORT_DATE
DEFAULT_UPDATE_INTERVAL: Final = 60
MIN_UPDATE_INTERVAL: Final = 15
MAX_UPDATE_INTERVAL: Final = 1440
DEFAULT_MIN_WORTH: Final = 0.0
DEFAULT_INCLUDE_NO_WORTH: Final = True
DEFAULT_EXCLUDE_KEYWORDS: Final = ""
DEFAULT_EXPIRING_HOURS: Final = 24
MAX_EXPIRING_HOURS: Final = 720

DEFAULT_OPTIONS: Final[dict[str, object]] = {
    CONF_SORT_BY: DEFAULT_SORT_BY,
    CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
    CONF_MIN_WORTH: DEFAULT_MIN_WORTH,
    CONF_INCLUDE_NO_WORTH: DEFAULT_INCLUDE_NO_WORTH,
    CONF_EXCLUDE_KEYWORDS: DEFAULT_EXCLUDE_KEYWORDS,
    CONF_EXPIRING_HOURS: DEFAULT_EXPIRING_HOURS,
}

EVENT_NEW_GIVEAWAY: Final = f"{DOMAIN}_new_giveaway"
EVENT_TYPE_NEW_GIVEAWAY: Final = "new_giveaway"

STORAGE_VERSION: Final = 1
SEEN_RETENTION: Final = timedelta(days=60)

# Recorder refuses to store attributes above 16 KiB; keep room for the
# attributes Home Assistant adds itself (friendly_name, attribution, ...).
MAX_ATTRIBUTES_BYTES: Final = 16384
RESERVED_ATTRIBUTES_BYTES: Final = 1024

ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"


def signal_new_giveaway(entry_id: str) -> str:
    """Return the dispatcher signal used for new giveaways of an entry."""
    return f"{DOMAIN}_new_giveaway_{entry_id}"


def storage_key(entry_id: str) -> str:
    """Return the Store key holding the seen giveaway IDs of an entry."""
    return f"{DOMAIN}.{entry_id}"
