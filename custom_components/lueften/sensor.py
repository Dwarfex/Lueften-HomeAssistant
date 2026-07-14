from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .binary_sensor import _RUNTIME_KEY, _RoomDiagnosticState
from .const import CONF_ENABLE_ADDITIONAL_INFO, DOMAIN

_SCOPE_ROOM = "room"
_METRIC_TEMPERATURE_DIFFERENCE = "temperature_difference_c"
_METRIC_HUMIDITY_DIFFERENCE = "humidity_difference_gm3"
_METRIC_SOURCE_TEMPERATURE = "source_temperature_c"
_METRIC_TARGET_TEMPERATURE = "target_temperature_c"
_METRIC_SOURCE_HUMIDITY = "source_humidity_gm3"
_METRIC_TARGET_HUMIDITY = "target_humidity_gm3"


@dataclass(frozen=True)
class _SensorDefinition:
    area_id: str
    area_name: str
    metric: str

    @property
    def key(self) -> str:
        return f"{self.area_id}:{self.metric}"

    @property
    def unique_id(self) -> str:
        return f"{_SCOPE_ROOM}_{self.area_id}_meta_{self.metric}"

    @property
    def translation_key(self) -> str:
        return f"room_{self.metric}"


class LueftenDiagnosticSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_domain = DOMAIN
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        runtime: "_LueftenSensorRuntime",
        definition: _SensorDefinition,
        *,
        enabled_by_default: bool,
    ) -> None:
        self._runtime = runtime
        self._definition = definition
        self._attr_unique_id = definition.unique_id
        self._attr_translation_key = definition.translation_key
        self._attr_translation_placeholders = {"target_name": definition.area_name}
        self._attr_entity_registry_enabled_default = enabled_by_default
        self._attr_entity_registry_visible_default = enabled_by_default

        if definition.metric in {
            _METRIC_TEMPERATURE_DIFFERENCE,
            _METRIC_SOURCE_TEMPERATURE,
            _METRIC_TARGET_TEMPERATURE,
        }:
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        else:
            self._attr_native_unit_of_measurement = "g/m³"

    @property
    def native_value(self) -> float | None:
        return self._runtime.value_for(self._definition.key)

    @callback
    def async_runtime_updated(self) -> None:
        if self.hass is None:
            return
        self.async_write_ha_state()


class _LueftenSensorRuntime:
    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._async_add_entities = async_add_entities
        self._definitions: dict[str, _SensorDefinition] = {}
        self._states: dict[str, float | None] = {}
        self._entities: dict[str, LueftenDiagnosticSensor] = {}
        self._unsubscribe_update_listener = None

    @callback
    def initialize(self) -> list[LueftenDiagnosticSensor]:
        self._build_definitions()
        self._refresh_states()
        self._unsubscribe_update_listener = self._binary_runtime.register_update_listener(
            self._handle_runtime_update
        )
        return [
            LueftenDiagnosticSensor(
                self,
                definition,
                enabled_by_default=True,
            )
            for definition in self._definitions.values()
        ]

    @property
    def _binary_runtime(self):
        return self._hass.data[_RUNTIME_KEY][self._entry.entry_id]

    @callback
    def _build_definitions(self) -> None:
        definitions: dict[str, _SensorDefinition] = {}
        for area_id, source in self._binary_runtime._room_sources.items():
            for metric in (
                _METRIC_TEMPERATURE_DIFFERENCE,
                _METRIC_HUMIDITY_DIFFERENCE,
                _METRIC_SOURCE_TEMPERATURE,
                _METRIC_TARGET_TEMPERATURE,
                _METRIC_SOURCE_HUMIDITY,
                _METRIC_TARGET_HUMIDITY,
            ):
                definition = _SensorDefinition(
                    area_id=area_id,
                    area_name=source.area_name,
                    metric=metric,
                )
                definitions[definition.key] = definition
        self._definitions = definitions

    @callback
    def _refresh_states(self) -> None:
        diagnostics = self._binary_runtime.room_diagnostics()
        states: dict[str, float | None] = {}

        for definition in self._definitions.values():
            value = self._value_from_diagnostic(diagnostics.get(definition.area_id), definition.metric)
            states[definition.key] = value

        self._states = states

    def _value_from_diagnostic(
        self,
        diagnostic: _RoomDiagnosticState | None,
        metric: str,
    ) -> float | None:
        if diagnostic is None:
            return None
        if metric == _METRIC_TEMPERATURE_DIFFERENCE:
            return diagnostic.temperature_difference_c
        if metric == _METRIC_HUMIDITY_DIFFERENCE:
            return diagnostic.humidity_difference_gm3
        if metric == _METRIC_SOURCE_TEMPERATURE:
            return diagnostic.indoor_temperature_c
        if metric == _METRIC_TARGET_TEMPERATURE:
            return diagnostic.outdoor_temperature_c
        if metric == _METRIC_SOURCE_HUMIDITY:
            return diagnostic.indoor_absolute_humidity_gm3
        if metric == _METRIC_TARGET_HUMIDITY:
            return diagnostic.outdoor_absolute_humidity_gm3
        return None

    @callback
    def value_for(self, key: str) -> float | None:
        return self._states.get(key)

    @callback
    def _handle_runtime_update(self) -> None:
        previous_definitions = dict(self._definitions)
        self._build_definitions()
        self._refresh_states()

        new_entities: list[LueftenDiagnosticSensor] = []
        for key, definition in self._definitions.items():
            if key in self._entities:
                continue
            entity = LueftenDiagnosticSensor(
                self,
                definition,
                enabled_by_default=True,
            )
            self._entities[key] = entity
            new_entities.append(entity)

        removed_keys = [key for key in self._entities if key not in self._definitions]
        for key in removed_keys:
            self._entities.pop(key, None)

        if new_entities:
            self._async_add_entities(new_entities)
        if previous_definitions != self._definitions:
            _remove_stale_registry_entities(self._hass, self._entry, self.expected_unique_ids())

        for entity in self._entities.values():
            entity.async_runtime_updated()

    @callback
    def register_entities(self, entities: list[LueftenDiagnosticSensor]) -> None:
        self._entities = {entity._definition.key: entity for entity in entities}

    @callback
    def expected_unique_ids(self) -> set[str]:
        return {definition.unique_id for definition in self._definitions.values()}

    @callback
    def shutdown(self) -> None:
        if self._unsubscribe_update_listener is not None:
            self._unsubscribe_update_listener()
            self._unsubscribe_update_listener = None


@callback
def _is_diagnostic_unique_id(unique_id: str | None) -> bool:
    return isinstance(unique_id, str) and unique_id.startswith("room_") and "_meta_" in unique_id


@callback
def _remove_stale_registry_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    expected_unique_ids: set[str],
) -> None:
    entity_registry = er.async_get(hass)
    for registry_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if registry_entry.domain != "sensor" or registry_entry.platform != DOMAIN:
            continue
        if not _is_diagnostic_unique_id(registry_entry.unique_id):
            continue
        if registry_entry.unique_id in expected_unique_ids:
            continue
        entity_registry.async_remove(registry_entry.entity_id)


@callback
def _activate_diagnostics_when_enabled(hass: HomeAssistant, entry: ConfigEntry) -> None:
    entity_registry = er.async_get(hass)
    for registry_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if registry_entry.domain != "sensor" or registry_entry.platform != DOMAIN:
            continue
        if not _is_diagnostic_unique_id(registry_entry.unique_id):
            continue
        if registry_entry.disabled_by is None and registry_entry.hidden_by is None:
            continue
        entity_registry.async_update_entity(
            registry_entry.entity_id,
            disabled_by=None,
            hidden_by=None,
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    options = hass.data[DOMAIN][entry.entry_id]
    enabled_by_default = bool(options.get(CONF_ENABLE_ADDITIONAL_INFO, False))

    if not enabled_by_default:
        _remove_stale_registry_entities(hass, entry, expected_unique_ids=set())
        return

    runtime = _LueftenSensorRuntime(hass, entry, async_add_entities)
    entities = runtime.initialize()
    runtime.register_entities(entities)
    _remove_stale_registry_entities(hass, entry, runtime.expected_unique_ids())

    _activate_diagnostics_when_enabled(hass, entry)

    if entities:
        async_add_entities(entities)
