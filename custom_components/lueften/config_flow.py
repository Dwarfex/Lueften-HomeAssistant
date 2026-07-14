from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .outdoor_candidates import (
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    discover_outdoor_candidates,
)

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
    CONF_OUTDOOR_HUMIDITY_ENTITY_ID,
    CONF_OUTDOOR_TEMPERATURE_ENTITY_ID,
    CONF_RESCAN_INTERVAL_MINUTES,
    CONF_ROOM_OUTDOOR_OVERRIDES,
    CONF_ROOM_THRESHOLD_OVERRIDES,
    DOMAIN,
)

_SENSOR_DOMAIN = "sensor"


def _state_device_classes(hass) -> dict[str, object]:
    return {
        state.entity_id: state.attributes.get("device_class")
        for state in hass.states.async_all(_SENSOR_DOMAIN)
    }


def _available_sensor_entity_ids(hass) -> set[str]:
    entity_registry = er.async_get(hass)
    registry_entity_ids = {
        entry.entity_id
        for entry in entity_registry.entities.values()
        if entry.domain == _SENSOR_DOMAIN
    }
    state_entity_ids = {state.entity_id for state in hass.states.async_all(_SENSOR_DOMAIN)}
    return registry_entity_ids | state_entity_ids


def _discover_outdoor_candidates(hass) -> tuple[list[str], list[str]]:
    entity_registry = er.async_get(hass)

    registry_sensor_entity_ids = {
        entry.entity_id
        for entry in entity_registry.entities.values()
        if entry.domain == _SENSOR_DOMAIN
    }
    state_device_classes = _state_device_classes(hass)
    all_sensor_entity_ids = registry_sensor_entity_ids | set(state_device_classes)

    registry_device_classes = {
        entity_id: (
            entity_registry.entities[entity_id].device_class
            if entity_id in entity_registry.entities
            else None
        )
        for entity_id in all_sensor_entity_ids
    }
    return discover_outdoor_candidates(
        entity_ids=all_sensor_entity_ids,
        registry_device_classes=registry_device_classes,
        state_device_classes=state_device_classes,
    )


def _resolve_area_id(
    entity_entry: er.RegistryEntry,
    device_registry: dr.DeviceRegistry,
) -> str | None:
    if entity_entry.area_id:
        return entity_entry.area_id

    if entity_entry.device_id:
        device_entry = device_registry.devices.get(entity_entry.device_id)
        if device_entry and device_entry.area_id:
            return device_entry.area_id

    return None


def _discover_room_sources(hass) -> list[tuple[str, str]]:
    area_registry = ar.async_get(hass)
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    room_area_ids: set[str] = set()
    for entry in entity_registry.entities.values():
        if entry.domain != _SENSOR_DOMAIN:
            continue
        if str(entry.device_class or "").strip().lower() not in {
            DEVICE_CLASS_TEMPERATURE,
            DEVICE_CLASS_HUMIDITY,
        }:
            continue

        area_id = _resolve_area_id(entry, device_registry)
        if area_id:
            room_area_ids.add(area_id)

    rooms: list[tuple[str, str]] = []
    for area_id in sorted(room_area_ids):
        area_entry = area_registry.areas.get(area_id)
        if area_entry is None:
            continue
        rooms.append((area_id, area_entry.name or area_id))

    return rooms


def _entity_selector(candidates: list[str]) -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            include_entities=candidates,
            multiple=False,
        )
    )


def _pick_default_required_entity(
    current_value: Any,
    candidates: list[str],
) -> str:
    current = str(current_value or "").strip()
    if current and current in candidates:
        return current
    if candidates:
        return candidates[0]
    return ""


def _build_options_schema(
    current: Mapping[str, Any],
    temperature_candidates: list[str],
    humidity_candidates: list[str],
) -> vol.Schema:
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
            vol.Required(
                CONF_OUTDOOR_TEMPERATURE_ENTITY_ID,
                default=_pick_default_required_entity(
                    current.get(CONF_OUTDOOR_TEMPERATURE_ENTITY_ID),
                    temperature_candidates,
                ),
            ): _entity_selector(temperature_candidates),
            vol.Optional(
                CONF_OUTDOOR_HUMIDITY_ENTITY_ID,
                default=str(current.get(CONF_OUTDOOR_HUMIDITY_ENTITY_ID, "")).strip(),
            ): _entity_selector(humidity_candidates),
            vol.Required(
                CONF_ROOM_THRESHOLD_OVERRIDES,
                default=_as_json_default(current[CONF_ROOM_THRESHOLD_OVERRIDES]),
            ): str,
        }
    )


def _build_room_override_schema(
    room_sources: list[tuple[str, str]],
    temperature_candidates: list[str],
    humidity_candidates: list[str],
    current_overrides: Mapping[str, Any],
) -> tuple[vol.Schema, dict[str, tuple[str, str]]]:
    fields: dict[Any, Any] = {}
    field_mapping: dict[str, tuple[str, str]] = {}

    for area_id, area_name in room_sources:
        room_override = current_overrides.get(area_id)
        if not isinstance(room_override, Mapping):
            room_override = {}

        temperature_key = f"{area_name} ({area_id}) → outdoor temperature"
        humidity_key = f"{area_name} ({area_id}) → outdoor humidity"

        field_mapping[temperature_key] = (area_id, CONF_OUTDOOR_TEMPERATURE_ENTITY_ID)
        field_mapping[humidity_key] = (area_id, CONF_OUTDOOR_HUMIDITY_ENTITY_ID)

        fields[
            vol.Optional(
                temperature_key,
                default=str(room_override.get(CONF_OUTDOOR_TEMPERATURE_ENTITY_ID, "")).strip(),
            )
        ] = _entity_selector(temperature_candidates)
        fields[
            vol.Optional(
                humidity_key,
                default=str(room_override.get(CONF_OUTDOOR_HUMIDITY_ENTITY_ID, "")).strip(),
            )
        ] = _entity_selector(humidity_candidates)

    return vol.Schema(fields), field_mapping


def _as_json_default(value: Any) -> str:
    if isinstance(value, Mapping):
        return json.dumps(value, indent=2, sort_keys=True)
    if isinstance(value, str):
        return value
    return ""


def _normalize_options(options: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(options)
    normalized[CONF_OUTDOOR_TEMPERATURE_ENTITY_ID] = str(
        options.get(CONF_OUTDOOR_TEMPERATURE_ENTITY_ID, "")
    ).strip()
    normalized[CONF_OUTDOOR_HUMIDITY_ENTITY_ID] = str(
        options.get(CONF_OUTDOOR_HUMIDITY_ENTITY_ID, "")
    ).strip()
    normalized[CONF_ROOM_THRESHOLD_OVERRIDES] = str(
        options.get(CONF_ROOM_THRESHOLD_OVERRIDES, "")
    ).strip()
    return normalized


class LueftenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        defaults = build_default_options()
        temperature_candidates, humidity_candidates = _discover_outdoor_candidates(self.hass)
        schema = _build_options_schema(
            defaults,
            temperature_candidates,
            humidity_candidates,
        )

        if user_input is not None:
            options = merge_entry_options(_normalize_options(user_input))
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
        self._pending_options: dict[str, Any] | None = None
        self._room_override_field_mapping: dict[str, tuple[str, str]] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        current = merge_entry_options(self._config_entry.options)
        temperature_candidates, humidity_candidates = _discover_outdoor_candidates(self.hass)
        schema = _build_options_schema(
            current,
            temperature_candidates,
            humidity_candidates,
        )

        if user_input is not None:
            self._pending_options = merge_entry_options(_normalize_options(user_input))
            return await self.async_step_room_overrides()

        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_room_overrides(self, user_input: dict[str, Any] | None = None):
        pending_options = self._pending_options or merge_entry_options(self._config_entry.options)
        room_sources = _discover_room_sources(self.hass)
        if not room_sources:
            return self.async_create_entry(title="", data=pending_options)

        temperature_candidates, humidity_candidates = _discover_outdoor_candidates(self.hass)
        current_overrides = pending_options.get(CONF_ROOM_OUTDOOR_OVERRIDES, {})
        if not isinstance(current_overrides, Mapping):
            current_overrides = {}

        schema, field_mapping = _build_room_override_schema(
            room_sources,
            temperature_candidates,
            humidity_candidates,
            current_overrides,
        )
        self._room_override_field_mapping = field_mapping

        errors: dict[str, str] = {}
        if user_input is not None:
            available_entity_ids = _available_sensor_entity_ids(self.hass)
            room_overrides: dict[str, dict[str, str]] = {}

            for field_name, (area_id, override_key) in self._room_override_field_mapping.items():
                entity_id = str(user_input.get(field_name, "")).strip()
                if not entity_id:
                    continue
                if entity_id not in available_entity_ids:
                    errors["base"] = "invalid_selected_entity"
                    break
                room_overrides.setdefault(area_id, {})[override_key] = entity_id

            if not errors:
                return self.async_create_entry(
                    title="",
                    data=merge_entry_options(
                        {
                            **pending_options,
                            CONF_ROOM_OUTDOOR_OVERRIDES: room_overrides,
                        }
                    ),
                )

        return self.async_show_form(
            step_id="room_overrides",
            data_schema=schema,
            errors=errors,
        )
