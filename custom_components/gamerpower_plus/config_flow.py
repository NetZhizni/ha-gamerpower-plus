"""Config flow for GamerPower Plus."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .api import GamerPowerError, async_create_client
from .const import (
    CONF_EXCLUDE_KEYWORDS,
    CONF_EXPIRING_HOURS,
    CONF_INCLUDE_NO_WORTH,
    CONF_MIN_WORTH,
    CONF_PLATFORMS,
    CONF_SORT_BY,
    CONF_TYPES,
    CONF_UPDATE_INTERVAL,
    DEFAULT_OPTIONS,
    DEFAULT_PLATFORMS,
    DEFAULT_TYPES,
    DOMAIN,
    GAMING_PLATFORMS,
    GIVEAWAY_TYPES,
    MAX_EXPIRING_HOURS,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    SORT_OPTIONS,
)
from .coordinator import async_remove_seen_store, parse_keywords

_LOGGER = logging.getLogger(__name__)


def ordered_selection(selected: Iterable[str], allowed: Iterable[str]) -> list[str]:
    """Return the valid selected values in canonical order, without duplicates."""
    chosen = set(selected)
    return [value for value in allowed if value in chosen]


def build_unique_id(platforms: Iterable[str], types: Iterable[str]) -> str:
    """Return the unique ID for a platform and type combination."""
    return f"{'.'.join(sorted(platforms))}|{'.'.join(sorted(types))}"


def build_title(platforms: Iterable[str], types: Iterable[str]) -> str:
    """Generate an entry title like ``Steam, Epic — game``."""
    platform_names = ", ".join(
        GAMING_PLATFORMS[p] for p in ordered_selection(platforms, GAMING_PLATFORMS)
    )
    type_names = ", ".join(ordered_selection(types, GIVEAWAY_TYPES))
    return f"{platform_names} — {type_names}"


def _filters_schema(platforms: list[str], types: list[str]) -> dict[vol.Marker, Any]:
    return {
        vol.Required(CONF_PLATFORMS, default=platforms): SelectSelector(
            SelectSelectorConfig(
                options=list(GAMING_PLATFORMS),
                multiple=True,
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="platform",
            )
        ),
        vol.Required(CONF_TYPES, default=types): SelectSelector(
            SelectSelectorConfig(
                options=list(GIVEAWAY_TYPES),
                multiple=True,
                mode=SelectSelectorMode.LIST,
                translation_key="giveaway_type",
            )
        ),
    }


def _options_schema(options: Mapping[str, Any]) -> dict[vol.Marker, Any]:
    values = {**DEFAULT_OPTIONS, **options}
    return {
        vol.Required(CONF_SORT_BY, default=values[CONF_SORT_BY]): SelectSelector(
            SelectSelectorConfig(
                options=list(SORT_OPTIONS),
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="sort_by",
            )
        ),
        vol.Required(
            CONF_UPDATE_INTERVAL, default=values[CONF_UPDATE_INTERVAL]
        ): vol.All(
            NumberSelector(
                NumberSelectorConfig(
                    min=MIN_UPDATE_INTERVAL,
                    max=MAX_UPDATE_INTERVAL,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="min",
                )
            ),
            vol.Coerce(int),
        ),
        vol.Required(CONF_MIN_WORTH, default=values[CONF_MIN_WORTH]): vol.All(
            NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=10000,
                    step=0.01,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="USD",
                )
            ),
            vol.Coerce(float),
        ),
        vol.Required(
            CONF_INCLUDE_NO_WORTH, default=values[CONF_INCLUDE_NO_WORTH]
        ): BooleanSelector(),
        vol.Optional(
            CONF_EXCLUDE_KEYWORDS,
            description={"suggested_value": values[CONF_EXCLUDE_KEYWORDS]},
        ): TextSelector(),
        vol.Required(CONF_EXPIRING_HOURS, default=values[CONF_EXPIRING_HOURS]): vol.All(
            NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=MAX_EXPIRING_HOURS,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="h",
                )
            ),
            vol.Coerce(int),
        ),
    }


def _extract_options(user_input: Mapping[str, Any]) -> dict[str, Any]:
    """Take the option values from a form submission, normalized."""
    options = {
        key: user_input.get(key, default) for key, default in DEFAULT_OPTIONS.items()
    }
    # An emptied text field is not submitted at all.
    options[CONF_EXCLUDE_KEYWORDS] = ", ".join(
        parse_keywords(user_input.get(CONF_EXCLUDE_KEYWORDS, ""))
    )
    return options


def _validate_filters(platforms: list[str], types: list[str]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not platforms:
        errors[CONF_PLATFORMS] = "no_platforms"
    if not types:
        errors[CONF_TYPES] = "no_types"
    return errors


class GamerPowerPlusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GamerPower Plus."""

    VERSION = 1
    MINOR_VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> GamerPowerPlusOptionsFlow:
        """Return the options flow."""
        return GamerPowerPlusOptionsFlow()

    async def _async_test_connection(
        self, platforms: list[str], types: list[str]
    ) -> dict[str, str]:
        client = async_create_client(self.hass)
        try:
            await client.async_get_giveaways(platforms, types)
        except GamerPowerError as err:
            _LOGGER.debug("Cannot connect to GamerPower: %s", err)
            return {"base": "cannot_connect"}
        except Exception:
            _LOGGER.exception("Unexpected error while testing GamerPower")
            return {"base": "unknown"}
        return {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create an entry from filters and options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            platforms = ordered_selection(user_input[CONF_PLATFORMS], GAMING_PLATFORMS)
            types = ordered_selection(user_input[CONF_TYPES], GIVEAWAY_TYPES)
            errors = _validate_filters(platforms, types)
            if not errors:
                await self.async_set_unique_id(build_unique_id(platforms, types))
                self._abort_if_unique_id_configured()
                errors = await self._async_test_connection(platforms, types)
            if not errors:
                title = (user_input.get(CONF_NAME) or "").strip() or build_title(
                    platforms, types
                )
                return self.async_create_entry(
                    title=title,
                    data={CONF_PLATFORMS: platforms, CONF_TYPES: types},
                    options=_extract_options(user_input),
                )

        values = user_input or {}
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_NAME, description={"suggested_value": values.get(CONF_NAME)}
                ): TextSelector(),
                **_filters_schema(
                    values.get(CONF_PLATFORMS, DEFAULT_PLATFORMS),
                    values.get(CONF_TYPES, DEFAULT_TYPES),
                ),
                **_options_schema(_extract_options(values) if values else {}),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the platforms and types of an entry."""
        entry = self._get_reconfigure_entry()
        old_platforms = list(entry.data[CONF_PLATFORMS])
        old_types = list(entry.data[CONF_TYPES])
        errors: dict[str, str] = {}

        if user_input is not None:
            platforms = ordered_selection(user_input[CONF_PLATFORMS], GAMING_PLATFORMS)
            types = ordered_selection(user_input[CONF_TYPES], GIVEAWAY_TYPES)
            errors = _validate_filters(platforms, types)
            unique_id = build_unique_id(platforms, types)
            if not errors and any(
                other.unique_id == unique_id and other.entry_id != entry.entry_id
                for other in self._async_current_entries(include_ignore=False)
            ):
                return self.async_abort(reason="already_configured")
            if not errors:
                errors = await self._async_test_connection(platforms, types)
            if not errors:
                title = entry.title
                if title == build_title(old_platforms, old_types):
                    title = build_title(platforms, types)
                if unique_id != entry.unique_id:
                    # Start over with a silent baseline instead of reporting
                    # every giveaway of the new selection as new.
                    await async_remove_seen_store(self.hass, entry.entry_id)
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=unique_id,
                    title=title,
                    data_updates={CONF_PLATFORMS: platforms, CONF_TYPES: types},
                )

        values = user_input or {}
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                _filters_schema(
                    values.get(CONF_PLATFORMS, old_platforms),
                    values.get(CONF_TYPES, old_types),
                )
            ),
            errors=errors,
        )


class GamerPowerPlusOptionsFlow(OptionsFlowWithReload):
    """Handle GamerPower Plus options; the entry reloads after saving."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=_extract_options(user_input))
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(_options_schema(self.config_entry.options)),
        )
