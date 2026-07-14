from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

from lueften_core import (
    FloorThresholds,
    RoomInputs,
    RoomRecommendation,
    aggregate_floor_recommendations,
    build_room_recommendation,
)
from lueften_core.sensor_selection import (
    RoomSensorKinds,
    determine_floor_sensor_kinds,
    determine_room_sensor_kinds,
)

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
    DEFAULT_FLOOR_THRESHOLD,
    DOMAIN,
    EVENT_RESCAN_REQUESTED,
)

_STATE_COLLECTION_DOMAIN = "sensor"
_SENSOR_KIND_TEMPERATURE = "temperature"
_SENSOR_KIND_HUMIDITY = "humidity"
_SENSOR_KIND_GENERIC = "generic"
_NO_FLOOR_ID = "no_floor"

_ROOM_SENSOR_LABELS = {
    _SENSOR_KIND_TEMPERATURE: "Lüften to reduce temperature",
    _SENSOR_KIND_HUMIDITY: "Lüften to reduce absolute humidity",
    _SENSOR_KIND_GENERIC: "Should Lüften",
}

_RUNTIME_KEY = f"{DOMAIN}_runtime"


@dataclass(frozen=True)
class _RoomSource:
    area_id: str
    area_name: str
    floor_id: str
    temperature_entity_id: str | None
    humidity_entity_id: str | None


@dataclass(frozen=True)
class _OutdoorSource:
    temperature_entity_id: str | None
    humidity_entity_id: str | None


@dataclass(frozen=True)
class _SensorDefinition:
    scope: str
    target_id: str
    target_name: str
    kind: str

    @property
    def key(self) -> str:
        return f"{self.scope}:{self.target_id}:{self.kind}"

    @property
    def unique_id(self) -> str:
        return f"{self.scope}_{self.target_id}_{self.kind}"


class LueftenBinarySensor(BinarySensorEntity):
    _attr_has_entity_name = False

    def __init__(self, runtime: "_LueftenRuntime", definition: _SensorDefinition) -> None:
        self._runtime = runtime
        self._definition = definition
        self._attr_unique_id = definition.unique_id
        self._attr_name = self._build_name(definition)

    @staticmethod
    def _build_name(definition: _SensorDefinition) -> str:
        return f"{definition.target_name} {_ROOM_SENSOR_LABELS[definition.kind]}"

    @property
    def is_on(self) -> bool | None:
        return self._runtime.state_for(self._definition.key)

    @callback
    def async_runtime_updated(self) -> None:
        self.async_write_ha_state()


class _LueftenRuntime:
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        options: dict[str, object],
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._options = options
        self._async_add_entities = async_add_entities

        self._definitions: dict[str, _SensorDefinition] = {}
        self._entities: dict[str, LueftenBinarySensor] = {}
        self._states: dict[str, bool | None] = {}

        self._room_sources: dict[str, _RoomSource] = {}
        self._room_kinds: dict[str, RoomSensorKinds] = {}
        self._outdoor_source = _OutdoorSource(None, None)
        self._floor_rooms: dict[str, list[str]] = defaultdict(list)

        self._source_entity_ids: set[str] = set()
        self._cleanup_callbacks: list[Callable[[], None]] = []
        self._cancel_state_listener: Callable[[], None] | None = None

    async def async_initialize(self) -> list[LueftenBinarySensor]:
        await self.async_rescan(add_new_entities=False)
        self._setup_listeners()
        return list(self._entities.values())

    def shutdown(self) -> None:
        if self._cancel_state_listener is not None:
            self._cancel_state_listener()
            self._cancel_state_listener = None

        while self._cleanup_callbacks:
            self._cleanup_callbacks.pop()()

    def state_for(self, key: str) -> bool | None:
        return self._states.get(key)

    @callback
    def _setup_listeners(self) -> None:
        @callback
        def _handle_rescan(_event: Event) -> None:
            self._hass.async_create_task(self.async_rescan())

        @callback
        def _handle_interval(_now) -> None:
            self._hass.async_create_task(self.async_rescan())

        self._cleanup_callbacks.append(self._hass.bus.async_listen(EVENT_RESCAN_REQUESTED, _handle_rescan))

        interval_minutes = self._option_int(CONF_RESCAN_INTERVAL_MINUTES, minimum=1)
        self._cleanup_callbacks.append(
            async_track_time_interval(
                self._hass,
                _handle_interval,
                timedelta(minutes=interval_minutes),
            )
        )

        self._reset_state_listener()

    @callback
    def _reset_state_listener(self) -> None:
        if self._cancel_state_listener is not None:
            self._cancel_state_listener()
            self._cancel_state_listener = None

        if not self._source_entity_ids:
            return

        @callback
        def _handle_state_change(_event: Event) -> None:
            self._refresh_states()
            self._push_state_updates()

        self._cancel_state_listener = async_track_state_change_event(
            self._hass,
            list(self._source_entity_ids),
            _handle_state_change,
        )

    async def async_rescan(self, add_new_entities: bool = True) -> None:
        room_sources, outdoor_source = self._discover_sources()
        room_kinds = self._build_room_kinds(room_sources, outdoor_source)
        floor_rooms = self._build_floor_room_map(room_sources, room_kinds)
        definitions = self._build_definitions(room_sources, room_kinds, floor_rooms)

        self._room_sources = room_sources
        self._room_kinds = room_kinds
        self._outdoor_source = outdoor_source
        self._floor_rooms = floor_rooms
        self._definitions = definitions

        previous_source_entity_ids = set(self._source_entity_ids)
        self._source_entity_ids = self._collect_source_entity_ids(room_sources, outdoor_source)

        new_entity_keys = [key for key in definitions if key not in self._entities]
        removed_entity_keys = [key for key in self._entities if key not in definitions]

        for key in removed_entity_keys:
            entity = self._entities.pop(key)
            await entity.async_remove(force_remove=True)
            self._states.pop(key, None)

        new_entities: list[LueftenBinarySensor] = []
        for key in new_entity_keys:
            entity = LueftenBinarySensor(self, definitions[key])
            self._entities[key] = entity
            new_entities.append(entity)

        self._refresh_states()

        if add_new_entities and new_entities:
            self._async_add_entities(new_entities)

        if self._source_entity_ids != previous_source_entity_ids:
            self._reset_state_listener()

        self._push_state_updates()

    @callback
    def _refresh_states(self) -> None:
        room_recommendations: dict[str, RoomRecommendation] = {}

        for area_id, source in self._room_sources.items():
            room_recommendation = build_room_recommendation(
                RoomInputs(
                    indoor_temperature_c=self._state_as_float(source.temperature_entity_id),
                    indoor_relative_humidity_pct=self._state_as_float(source.humidity_entity_id),
                    outdoor_temperature_c=self._state_as_float(self._outdoor_source.temperature_entity_id),
                    outdoor_relative_humidity_pct=self._state_as_float(self._outdoor_source.humidity_entity_id),
                    enable_temperature=self._option_bool(CONF_ENABLE_TEMPERATURE),
                    enable_humidity=self._option_bool(CONF_ENABLE_HUMIDITY),
                    include_generic=self._option_bool(CONF_INCLUDE_GENERIC),
                    temperature_delta_c=self._option_float(CONF_DEFAULT_TEMPERATURE_DELTA_C),
                    humidity_delta_gm3=self._option_float(CONF_DEFAULT_HUMIDITY_DELTA_GM3),
                )
            )
            room_recommendations[area_id] = room_recommendation

            room_kinds = self._room_kinds.get(area_id)
            if room_kinds is None:
                continue

            if room_kinds.temperature:
                self._states[f"room:{area_id}:{_SENSOR_KIND_TEMPERATURE}"] = room_recommendation.temperature
            if room_kinds.humidity:
                self._states[f"room:{area_id}:{_SENSOR_KIND_HUMIDITY}"] = room_recommendation.humidity
            if room_kinds.generic:
                self._states[f"room:{area_id}:{_SENSOR_KIND_GENERIC}"] = room_recommendation.generic

        thresholds = FloorThresholds(
            temperature=self._option_int(CONF_FLOOR_THRESHOLD_TEMPERATURE, minimum=1),
            humidity=self._option_int(CONF_FLOOR_THRESHOLD_HUMIDITY, minimum=1),
            generic=self._option_int(CONF_FLOOR_THRESHOLD_GENERIC, minimum=1),
        )

        for floor_id, room_ids in self._floor_rooms.items():
            room_values = [
                room_recommendations[room_id]
                for room_id in room_ids
                if room_id in room_recommendations
            ]
            floor_recommendation = aggregate_floor_recommendations(room_values, thresholds)

            floor_room_kinds = [
                self._room_kinds[room_id] for room_id in room_ids if room_id in self._room_kinds
            ]
            floor_kinds = determine_floor_sensor_kinds(
                floor_room_kinds,
                include_generic=self._option_bool(CONF_INCLUDE_GENERIC),
            )
            if floor_kinds.temperature:
                self._states[f"floor:{floor_id}:{_SENSOR_KIND_TEMPERATURE}"] = floor_recommendation.temperature
            if floor_kinds.humidity:
                self._states[f"floor:{floor_id}:{_SENSOR_KIND_HUMIDITY}"] = floor_recommendation.humidity
            if floor_kinds.generic:
                self._states[f"floor:{floor_id}:{_SENSOR_KIND_GENERIC}"] = floor_recommendation.generic

    @callback
    def _push_state_updates(self) -> None:
        for entity in self._entities.values():
            entity.async_runtime_updated()

    def _discover_sources(self) -> tuple[dict[str, _RoomSource], _OutdoorSource]:
        area_reg = ar.async_get(self._hass)
        entity_reg = er.async_get(self._hass)
        device_reg = dr.async_get(self._hass)

        by_area: dict[str, dict[str, list[str]]] = defaultdict(
            lambda: {_SENSOR_KIND_TEMPERATURE: [], _SENSOR_KIND_HUMIDITY: []}
        )
        outdoor_temperature_candidates: list[str] = []
        outdoor_humidity_candidates: list[str] = []

        for state in self._hass.states.async_all(_STATE_COLLECTION_DOMAIN):
            device_class = state.attributes.get(ATTR_DEVICE_CLASS)
            if device_class not in (_SENSOR_KIND_TEMPERATURE, _SENSOR_KIND_HUMIDITY):
                continue

            area_id = self._resolve_area_id(state.entity_id, entity_reg, device_reg)
            if area_id is None:
                if device_class == _SENSOR_KIND_TEMPERATURE:
                    outdoor_temperature_candidates.append(state.entity_id)
                else:
                    outdoor_humidity_candidates.append(state.entity_id)
                continue

            by_area[area_id][device_class].append(state.entity_id)

        room_sources: dict[str, _RoomSource] = {}
        for area_entry in area_reg.areas.values():
            if area_entry.id not in by_area:
                continue

            room_temperature_entities = sorted(by_area[area_entry.id][_SENSOR_KIND_TEMPERATURE])
            room_humidity_entities = sorted(by_area[area_entry.id][_SENSOR_KIND_HUMIDITY])

            room_sources[area_entry.id] = _RoomSource(
                area_id=area_entry.id,
                area_name=area_entry.name,
                floor_id=area_entry.floor_id or _NO_FLOOR_ID,
                temperature_entity_id=room_temperature_entities[0] if room_temperature_entities else None,
                humidity_entity_id=room_humidity_entities[0] if room_humidity_entities else None,
            )

        return room_sources, self._resolve_outdoor_source(
            sorted(outdoor_temperature_candidates),
            sorted(outdoor_humidity_candidates),
        )

    def _resolve_outdoor_source(
        self,
        temperature_candidates: list[str],
        humidity_candidates: list[str],
    ) -> _OutdoorSource:
        configured_temperature_entity = self._option_string(CONF_OUTDOOR_TEMPERATURE_ENTITY_ID)
        configured_humidity_entity = self._option_string(CONF_OUTDOOR_HUMIDITY_ENTITY_ID)

        selected_temperature_entity = configured_temperature_entity
        if not selected_temperature_entity:
            selected_temperature_entity = temperature_candidates[0] if temperature_candidates else None

        selected_humidity_entity = configured_humidity_entity
        if not selected_humidity_entity:
            selected_humidity_entity = humidity_candidates[0] if humidity_candidates else None

        if selected_temperature_entity and self._hass.states.get(selected_temperature_entity) is None:
            selected_temperature_entity = None
        if selected_humidity_entity and self._hass.states.get(selected_humidity_entity) is None:
            selected_humidity_entity = None

        return _OutdoorSource(
            temperature_entity_id=selected_temperature_entity,
            humidity_entity_id=selected_humidity_entity,
        )

    @staticmethod
    def _resolve_area_id(
        entity_id: str,
        entity_reg: er.EntityRegistry,
        device_reg: dr.DeviceRegistry,
    ) -> str | None:
        entity_entry = entity_reg.async_get(entity_id)
        if entity_entry is None or entity_entry.disabled_by is not None:
            return None

        if entity_entry.area_id:
            return entity_entry.area_id

        if entity_entry.device_id:
            device_entry = device_reg.async_get(entity_entry.device_id)
            if device_entry and device_entry.area_id:
                return device_entry.area_id

        return None

    def _build_room_kinds(
        self,
        room_sources: dict[str, _RoomSource],
        outdoor_source: _OutdoorSource,
    ) -> dict[str, RoomSensorKinds]:
        room_kinds: dict[str, RoomSensorKinds] = {}

        has_outdoor_temperature = outdoor_source.temperature_entity_id is not None
        has_outdoor_humidity = outdoor_source.humidity_entity_id is not None

        for area_id, room_source in room_sources.items():
            kinds = determine_room_sensor_kinds(
                has_indoor_temperature=room_source.temperature_entity_id is not None and has_outdoor_temperature,
                has_indoor_humidity=(
                    room_source.temperature_entity_id is not None
                    and room_source.humidity_entity_id is not None
                    and has_outdoor_temperature
                    and has_outdoor_humidity
                ),
                enable_temperature=self._option_bool(CONF_ENABLE_TEMPERATURE),
                enable_humidity=self._option_bool(CONF_ENABLE_HUMIDITY),
                include_generic=self._option_bool(CONF_INCLUDE_GENERIC),
            )
            if not (kinds.temperature or kinds.humidity or kinds.generic):
                continue
            room_kinds[area_id] = kinds

        return room_kinds

    @staticmethod
    def _build_floor_room_map(
        room_sources: dict[str, _RoomSource],
        room_kinds: dict[str, RoomSensorKinds],
    ) -> dict[str, list[str]]:
        floors: dict[str, list[str]] = defaultdict(list)
        for area_id, source in room_sources.items():
            if area_id not in room_kinds:
                continue
            floors[source.floor_id].append(area_id)
        return floors

    def _build_definitions(
        self,
        room_sources: dict[str, _RoomSource],
        room_kinds: dict[str, RoomSensorKinds],
        floor_rooms: dict[str, list[str]],
    ) -> dict[str, _SensorDefinition]:
        definitions: dict[str, _SensorDefinition] = {}

        for area_id, kinds in room_kinds.items():
            room = room_sources[area_id]
            for kind, enabled in (
                (_SENSOR_KIND_TEMPERATURE, kinds.temperature),
                (_SENSOR_KIND_HUMIDITY, kinds.humidity),
                (_SENSOR_KIND_GENERIC, kinds.generic),
            ):
                if not enabled:
                    continue
                definition = _SensorDefinition(
                    scope="room",
                    target_id=area_id,
                    target_name=room.area_name,
                    kind=kind,
                )
                definitions[definition.key] = definition

        for floor_id, room_ids in floor_rooms.items():
            floor_kinds = determine_floor_sensor_kinds(
                [room_kinds[room_id] for room_id in room_ids],
                include_generic=self._option_bool(CONF_INCLUDE_GENERIC),
            )
            floor_name = "No floor" if floor_id == _NO_FLOOR_ID else f"Floor {floor_id}"
            for kind, enabled in (
                (_SENSOR_KIND_TEMPERATURE, floor_kinds.temperature),
                (_SENSOR_KIND_HUMIDITY, floor_kinds.humidity),
                (_SENSOR_KIND_GENERIC, floor_kinds.generic),
            ):
                if not enabled:
                    continue
                definition = _SensorDefinition(
                    scope="floor",
                    target_id=floor_id,
                    target_name=floor_name,
                    kind=kind,
                )
                definitions[definition.key] = definition

        return definitions

    @staticmethod
    def _collect_source_entity_ids(
        room_sources: dict[str, _RoomSource],
        outdoor_source: _OutdoorSource,
    ) -> set[str]:
        source_entity_ids: set[str] = set()
        for source in room_sources.values():
            if source.temperature_entity_id:
                source_entity_ids.add(source.temperature_entity_id)
            if source.humidity_entity_id:
                source_entity_ids.add(source.humidity_entity_id)
        if outdoor_source.temperature_entity_id:
            source_entity_ids.add(outdoor_source.temperature_entity_id)
        if outdoor_source.humidity_entity_id:
            source_entity_ids.add(outdoor_source.humidity_entity_id)
        return source_entity_ids

    def _state_as_float(self, entity_id: str | None) -> float | None:
        if entity_id is None:
            return None

        state = self._hass.states.get(entity_id)
        if state is None:
            return None

        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    def _option_bool(self, key: str) -> bool:
        return bool(self._options.get(key))

    def _option_float(self, key: str) -> float:
        try:
            return float(self._options.get(key, 0.0))
        except (TypeError, ValueError):
            return 0.0

    def _option_int(self, key: str, minimum: int) -> int:
        try:
            value = int(self._options.get(key, DEFAULT_FLOOR_THRESHOLD))
        except (TypeError, ValueError):
            value = DEFAULT_FLOOR_THRESHOLD
        return max(value, minimum)

    def _option_string(self, key: str) -> str | None:
        value = self._options.get(key)
        if value is None:
            return None
        text = str(value).strip()
        return text or None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    options = hass.data[DOMAIN][entry.entry_id]
    runtime = _LueftenRuntime(hass, entry, options, async_add_entities)

    runtimes = hass.data.setdefault(_RUNTIME_KEY, {})
    runtimes[entry.entry_id] = runtime

    entities = await runtime.async_initialize()
    if entities:
        async_add_entities(entities)

    def _cleanup_runtime() -> None:
        runtime.shutdown()
        hass.data.get(_RUNTIME_KEY, {}).pop(entry.entry_id, None)

    entry.async_on_unload(_cleanup_runtime)
