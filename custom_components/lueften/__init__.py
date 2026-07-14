from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    CONF_DEFAULT_HUMIDITY_DELTA_GM3,
    CONF_DEFAULT_TEMPERATURE_DELTA_C,
    CONF_ENABLE_HUMIDITY,
    CONF_ENABLE_TEMPERATURE,
    CONF_FLOOR_THRESHOLD_GENERIC,
    CONF_FLOOR_THRESHOLD_HUMIDITY,
    CONF_FLOOR_THRESHOLD_TEMPERATURE,
    CONF_INCLUDE_GENERIC,
    CONF_OUTDOOR_HUMIDITY_ENTITY_ID,
    CONF_OUTDOOR_TEMPERATURE_ENTITY_ID,
    CONF_RESCAN_INTERVAL_MINUTES,
    DEFAULT_ENABLE_HUMIDITY,
    DEFAULT_ENABLE_TEMPERATURE,
    DEFAULT_FLOOR_THRESHOLD,
    DEFAULT_HUMIDITY_DELTA_GM3,
    DEFAULT_INCLUDE_GENERIC,
    DEFAULT_OUTDOOR_HUMIDITY_ENTITY_ID,
    DEFAULT_OUTDOOR_TEMPERATURE_ENTITY_ID,
    DEFAULT_RESCAN_INTERVAL_MINUTES,
    DEFAULT_TEMPERATURE_DELTA_C,
    DOMAIN,
    EVENT_RESCAN_REQUESTED,
    SERVICE_REQUEST_RESCAN,
)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR]


def build_default_options() -> dict[str, Any]:
    return {
        CONF_ENABLE_TEMPERATURE: DEFAULT_ENABLE_TEMPERATURE,
        CONF_ENABLE_HUMIDITY: DEFAULT_ENABLE_HUMIDITY,
        CONF_INCLUDE_GENERIC: DEFAULT_INCLUDE_GENERIC,
        CONF_DEFAULT_TEMPERATURE_DELTA_C: DEFAULT_TEMPERATURE_DELTA_C,
        CONF_DEFAULT_HUMIDITY_DELTA_GM3: DEFAULT_HUMIDITY_DELTA_GM3,
        CONF_FLOOR_THRESHOLD_TEMPERATURE: DEFAULT_FLOOR_THRESHOLD,
        CONF_FLOOR_THRESHOLD_HUMIDITY: DEFAULT_FLOOR_THRESHOLD,
        CONF_FLOOR_THRESHOLD_GENERIC: DEFAULT_FLOOR_THRESHOLD,
        CONF_RESCAN_INTERVAL_MINUTES: DEFAULT_RESCAN_INTERVAL_MINUTES,
        CONF_OUTDOOR_TEMPERATURE_ENTITY_ID: DEFAULT_OUTDOOR_TEMPERATURE_ENTITY_ID,
        CONF_OUTDOOR_HUMIDITY_ENTITY_ID: DEFAULT_OUTDOOR_HUMIDITY_ENTITY_ID,
    }


def merge_entry_options(options: Mapping[str, Any]) -> dict[str, Any]:
    merged = build_default_options()
    merged.update(options)
    return merged


async def _async_handle_rescan_service(call: ServiceCall, hass: HomeAssistant) -> None:
    hass.bus.async_fire(EVENT_RESCAN_REQUESTED, {"source": "service", **call.data})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = merge_entry_options(entry.options)

    if not hass.services.has_service(DOMAIN, SERVICE_REQUEST_RESCAN):
        async def _service_handler(call: ServiceCall) -> None:
            await _async_handle_rescan_service(call, hass)

        hass.services.async_register(
            DOMAIN,
            SERVICE_REQUEST_RESCAN,
            _service_handler,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    if not hass.data.get(DOMAIN) and hass.services.has_service(DOMAIN, SERVICE_REQUEST_RESCAN):
        hass.services.async_remove(DOMAIN, SERVICE_REQUEST_RESCAN)

    return unload_ok
