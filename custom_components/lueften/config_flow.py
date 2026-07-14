from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry

from . import build_default_options, merge_entry_options
from .const import (
    CONF_DEFAULT_HUMIDITY_DELTA_GM3,
    CONF_DEFAULT_TEMPERATURE_DELTA_C,
    CONF_ENABLE_HUMIDITY,
    CONF_ENABLE_TEMPERATURE,
    CONF_FLOOR_THRESHOLD_GENERIC,
    CONF_FLOOR_THRESHOLD_HUMIDITY,
    CONF_FLOOR_THRESHOLD_TEMPERATURE,
    CONF_INCLUDE_GENERIC,
    CONF_RESCAN_INTERVAL_MINUTES,
    DOMAIN,
)


def _build_options_schema(current: Mapping[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_ENABLE_TEMPERATURE,
                default=current[CONF_ENABLE_TEMPERATURE],
            ): bool,
            vol.Required(
                CONF_ENABLE_HUMIDITY,
                default=current[CONF_ENABLE_HUMIDITY],
            ): bool,
            vol.Required(
                CONF_INCLUDE_GENERIC,
                default=current[CONF_INCLUDE_GENERIC],
            ): bool,
            vol.Required(
                CONF_DEFAULT_TEMPERATURE_DELTA_C,
                default=current[CONF_DEFAULT_TEMPERATURE_DELTA_C],
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0)),
            vol.Required(
                CONF_DEFAULT_HUMIDITY_DELTA_GM3,
                default=current[CONF_DEFAULT_HUMIDITY_DELTA_GM3],
            ): vol.All(vol.Coerce(float), vol.Range(min=0.0)),
            vol.Required(
                CONF_FLOOR_THRESHOLD_TEMPERATURE,
                default=current[CONF_FLOOR_THRESHOLD_TEMPERATURE],
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Required(
                CONF_FLOOR_THRESHOLD_HUMIDITY,
                default=current[CONF_FLOOR_THRESHOLD_HUMIDITY],
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Required(
                CONF_FLOOR_THRESHOLD_GENERIC,
                default=current[CONF_FLOOR_THRESHOLD_GENERIC],
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Required(
                CONF_RESCAN_INTERVAL_MINUTES,
                default=current[CONF_RESCAN_INTERVAL_MINUTES],
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
        }
    )


class LueftenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        defaults = build_default_options()
        schema = _build_options_schema(defaults)

        if user_input is not None:
            options = merge_entry_options(user_input)
            return self.async_create_entry(
                title="Lüften",
                data={},
                options=options,
            )

        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry):
        return LueftenOptionsFlow(config_entry)


class LueftenOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        current = merge_entry_options(self._config_entry.options)
        schema = _build_options_schema(current)

        if user_input is not None:
            return self.async_create_entry(title="", data=merge_entry_options(user_input))

        return self.async_show_form(step_id="init", data_schema=schema)
