from __future__ import annotations

import json
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
    CONF_FLOOR_OUTDOOR_OVERRIDES,
    CONF_INCLUDE_GENERIC,
    CONF_OUTDOOR_HUMIDITY_ENTITY_ID,
    CONF_OUTDOOR_TEMPERATURE_ENTITY_ID,
    CONF_RESCAN_INTERVAL_MINUTES,
    CONF_ROOM_HUMIDITY_DELTA_GM3,
    CONF_ROOM_TEMPERATURE_DELTA_C,
    CONF_ROOM_THRESHOLD_OVERRIDES,
    DEFAULT_FLOOR_OUTDOOR_OVERRIDES,
    DEFAULT_ENABLE_HUMIDITY,
    DEFAULT_ENABLE_TEMPERATURE,
    DEFAULT_FLOOR_THRESHOLD,
    DEFAULT_HUMIDITY_DELTA_GM3,
    DEFAULT_INCLUDE_GENERIC,
    DEFAULT_OUTDOOR_HUMIDITY_ENTITY_ID,
    DEFAULT_OUTDOOR_TEMPERATURE_ENTITY_ID,
    DEFAULT_RESCAN_INTERVAL_MINUTES,
    DEFAULT_ROOM_THRESHOLD_OVERRIDES,
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
        CONF_ROOM_THRESHOLD_OVERRIDES: dict(DEFAULT_ROOM_THRESHOLD_OVERRIDES),
        CONF_FLOOR_OUTDOOR_OVERRIDES: dict(DEFAULT_FLOOR_OUTDOOR_OVERRIDES),
    }


def _load_override_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, Mapping):
            return parsed

    return {}


def _as_non_negative_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None

    if parsed < 0.0:
        return None
    return parsed


def _normalize_entity_id(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_room_threshold_overrides(value: Any) -> dict[str, dict[str, float]]:
    normalized: dict[str, dict[str, float]] = {}

    for room_id, raw_override in _load_override_mapping(value).items():
        room_key = str(room_id).strip()
        if not room_key or not isinstance(raw_override, Mapping):
            continue

        parsed_override: dict[str, float] = {}
        temperature_delta = _as_non_negative_float(
            raw_override.get(CONF_ROOM_TEMPERATURE_DELTA_C)
        )
        if temperature_delta is not None:
            parsed_override[CONF_ROOM_TEMPERATURE_DELTA_C] = temperature_delta

        humidity_delta = _as_non_negative_float(
            raw_override.get(CONF_ROOM_HUMIDITY_DELTA_GM3)
        )
        if humidity_delta is not None:
            parsed_override[CONF_ROOM_HUMIDITY_DELTA_GM3] = humidity_delta

        if parsed_override:
            normalized[room_key] = parsed_override

    return normalized


def _normalize_floor_outdoor_overrides(value: Any) -> dict[str, dict[str, str]]:
    normalized: dict[str, dict[str, str]] = {}

    for floor_id, raw_override in _load_override_mapping(value).items():
        floor_key = str(floor_id).strip()
        if not floor_key or not isinstance(raw_override, Mapping):
            continue

        parsed_override: dict[str, str] = {}
        temperature_entity_id = _normalize_entity_id(
            raw_override.get(CONF_OUTDOOR_TEMPERATURE_ENTITY_ID)
        )
        if temperature_entity_id:
            parsed_override[CONF_OUTDOOR_TEMPERATURE_ENTITY_ID] = temperature_entity_id

        humidity_entity_id = _normalize_entity_id(
            raw_override.get(CONF_OUTDOOR_HUMIDITY_ENTITY_ID)
        )
        if humidity_entity_id:
            parsed_override[CONF_OUTDOOR_HUMIDITY_ENTITY_ID] = humidity_entity_id

        if parsed_override:
            normalized[floor_key] = parsed_override

    return normalized


def merge_entry_options(options: Mapping[str, Any]) -> dict[str, Any]:
    merged = build_default_options()
    merged.update(options)

    merged[CONF_OUTDOOR_TEMPERATURE_ENTITY_ID] = _normalize_entity_id(
        merged.get(CONF_OUTDOOR_TEMPERATURE_ENTITY_ID)
    ) or DEFAULT_OUTDOOR_TEMPERATURE_ENTITY_ID
    merged[CONF_OUTDOOR_HUMIDITY_ENTITY_ID] = _normalize_entity_id(
        merged.get(CONF_OUTDOOR_HUMIDITY_ENTITY_ID)
    ) or DEFAULT_OUTDOOR_HUMIDITY_ENTITY_ID
    merged[CONF_ROOM_THRESHOLD_OVERRIDES] = _normalize_room_threshold_overrides(
        merged.get(CONF_ROOM_THRESHOLD_OVERRIDES)
    )
    merged[CONF_FLOOR_OUTDOOR_OVERRIDES] = _normalize_floor_outdoor_overrides(
        merged.get(CONF_FLOOR_OUTDOOR_OVERRIDES)
    )

    return merged


async def _async_handle_rescan_service(call: ServiceCall, hass: HomeAssistant) -> None:
    hass.bus.async_fire(EVENT_RESCAN_REQUESTED, {"source": "service", **call.data})


async def _async_handle_options_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = merge_entry_options(entry.options)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = merge_entry_options(entry.options)
    entry.async_on_unload(entry.add_update_listener(_async_handle_options_update))

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
