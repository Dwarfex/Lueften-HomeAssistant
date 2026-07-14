from pathlib import Path

from lueften_core.logic import (
    FloorThresholds,
    RoomInputs,
    RoomRecommendation,
    absolute_humidity_gm3,
    aggregate_floor_recommendations,
    build_room_recommendation,
    should_lueften_for_humidity,
    should_lueften_for_temperature,
)
from lueften_core.outdoor_candidates import discover_outdoor_candidates
from lueften_core.override_resolution import (
    resolve_outdoor_source_entities,
    resolve_room_threshold_values,
    select_first_available_entity,
)
from lueften_core.sensor_selection import (
    RoomSensorKinds,
    determine_floor_sensor_kinds,
    determine_room_sensor_kinds,
)


def test_absolute_humidity_returns_expected_range() -> None:
    # Around 8.6 g/m³ at 10°C and 90% RH
    value = absolute_humidity_gm3(10.0, 90.0)
    assert value is not None
    assert 8.0 < value < 9.5


def test_temperature_recommendation_threshold_logic() -> None:
    assert should_lueften_for_temperature(23.0, 21.5, min_delta_c=1.0) is True
    assert should_lueften_for_temperature(23.0, 22.2, min_delta_c=1.0) is False


def test_humidity_recommendation_threshold_logic() -> None:
    # Typical case where indoor absolute humidity is higher than outdoor.
    assert should_lueften_for_humidity(22.0, 60.0, 10.0, 70.0, min_delta_gm3=1.0) is True


def test_room_generic_any_logic() -> None:
    recommendation = build_room_recommendation(
        RoomInputs(
            indoor_temperature_c=23.0,
            indoor_relative_humidity_pct=40.0,
            outdoor_temperature_c=21.0,
            outdoor_relative_humidity_pct=95.0,
            enable_temperature=True,
            enable_humidity=True,
            include_generic=True,
            temperature_delta_c=1.0,
            humidity_delta_gm3=1.0,
        )
    )
    assert recommendation.temperature is True
    assert recommendation.humidity is False
    assert recommendation.generic is True


def test_floor_aggregation_per_type_threshold() -> None:
    floor = aggregate_floor_recommendations(
        room_recommendations=[
            RoomRecommendation(temperature=True, humidity=False, generic=True),
            RoomRecommendation(temperature=True, humidity=True, generic=True),
            RoomRecommendation(temperature=False, humidity=True, generic=True),
        ],
        thresholds=FloorThresholds(temperature=2, humidity=2, generic=3),
    )

    assert floor.temperature is True
    assert floor.humidity is True
    assert floor.generic is True


def test_floor_aggregation_ignores_unavailable_rooms() -> None:
    floor = aggregate_floor_recommendations(
        room_recommendations=[
            RoomRecommendation(temperature=None, humidity=None, generic=None),
            RoomRecommendation(temperature=True, humidity=None, generic=True),
        ],
        thresholds=FloorThresholds(temperature=1, humidity=1, generic=1),
    )

    assert floor.temperature is True
    assert floor.humidity is None
    assert floor.generic is True


def test_room_sensor_selection_skips_unavailable_requirements() -> None:
    kinds = determine_room_sensor_kinds(
        has_indoor_temperature=False,
        has_indoor_humidity=True,
        enable_temperature=True,
        enable_humidity=True,
        include_generic=True,
    )

    assert kinds == RoomSensorKinds(temperature=False, humidity=False, generic=False)


def test_room_sensor_selection_allows_temperature_only_path() -> None:
    kinds = determine_room_sensor_kinds(
        has_indoor_temperature=True,
        has_indoor_humidity=False,
        enable_temperature=True,
        enable_humidity=False,
        include_generic=True,
    )

    assert kinds == RoomSensorKinds(temperature=True, humidity=False, generic=True)


def test_discover_outdoor_candidates_uses_state_device_class_fallback() -> None:
    temperature_candidates, humidity_candidates = discover_outdoor_candidates(
        entity_ids={
            "sensor.app_battery_temperature",
            "sensor.weather_station_outdoor_temperature",
            "sensor.weather_station_outdoor_humidity",
            "sensor.energy_power",
        },
        registry_device_classes={
            "sensor.app_battery_temperature": "temperature",
            "sensor.weather_station_outdoor_temperature": None,
            "sensor.weather_station_outdoor_humidity": None,
            "sensor.energy_power": "power",
        },
        state_device_classes={
            "sensor.weather_station_outdoor_temperature": "temperature",
            "sensor.weather_station_outdoor_humidity": "humidity",
        },
    )

    assert temperature_candidates == [
        "sensor.app_battery_temperature",
        "sensor.weather_station_outdoor_temperature",
    ]
    assert humidity_candidates == ["sensor.weather_station_outdoor_humidity"]


def test_config_flow_has_no_external_outdoor_candidates_import() -> None:
    config_flow_source = (
        Path(__file__).resolve().parents[1] / "custom_components" / "lueften" / "config_flow.py"
    ).read_text(encoding="utf-8")

    assert "from lueften_core.outdoor_candidates import" not in config_flow_source


def test_binary_sensor_has_no_external_lueften_core_imports() -> None:
    binary_sensor_source = (
        Path(__file__).resolve().parents[1] / "custom_components" / "lueften" / "binary_sensor.py"
    ).read_text(encoding="utf-8")

    assert "from lueften_core import" not in binary_sensor_source
    assert "from lueften_core." not in binary_sensor_source


def test_binary_sensor_defines_device_info_for_integration_visibility() -> None:
    binary_sensor_source = (
        Path(__file__).resolve().parents[1] / "custom_components" / "lueften" / "binary_sensor.py"
    ).read_text(encoding="utf-8")

    assert "self._attr_device_info = runtime.device_info_for(definition)" in binary_sensor_source
    assert '"identifiers"' in binary_sensor_source
    assert "suggested_area" in binary_sensor_source


def test_binary_sensor_runs_discovery_during_setup() -> None:
    binary_sensor_source = (
        Path(__file__).resolve().parents[1] / "custom_components" / "lueften" / "binary_sensor.py"
    ).read_text(encoding="utf-8")

    assert "entities = await runtime.async_initialize()" in binary_sensor_source


def test_binary_sensor_runtime_update_is_safe_before_entity_is_added() -> None:
    binary_sensor_source = (
        Path(__file__).resolve().parents[1] / "custom_components" / "lueften" / "binary_sensor.py"
    ).read_text(encoding="utf-8")

    assert "if self.hass is None:" in binary_sensor_source


def test_binary_sensor_uses_entity_name_translation_mode() -> None:
    binary_sensor_source = (
        Path(__file__).resolve().parents[1] / "custom_components" / "lueften" / "binary_sensor.py"
    ).read_text(encoding="utf-8")

    assert "_attr_has_entity_name = True" in binary_sensor_source
    assert "_attr_translation_domain = DOMAIN" in binary_sensor_source


def test_binary_sensor_migrates_legacy_entity_names() -> None:
    binary_sensor_source = (
        Path(__file__).resolve().parents[1] / "custom_components" / "lueften" / "binary_sensor.py"
    ).read_text(encoding="utf-8")

    assert "def _migrate_legacy_entity_names" in binary_sensor_source
    assert "entity_registry.async_update_entity(registry_entry.entity_id, name=None)" in binary_sensor_source
    assert "_migrate_legacy_entity_names(hass, entry)" in binary_sensor_source


def test_binary_sensor_names_include_reason_prefix() -> None:
    strings_source = (
        Path(__file__).resolve().parents[1] / "custom_components" / "lueften" / "strings.json"
    ).read_text(encoding="utf-8")
    de_translation_source = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "lueften"
        / "translations"
        / "de.json"
    ).read_text(encoding="utf-8")

    assert '"Lüften: Senken Temperatur ({target_name})"' in strings_source
    assert '"Lüften: Senken Luftfeuchte ({target_name})"' in strings_source
    assert '"Lüften: Generisch ({target_name})"' in strings_source
    assert '"Lüften: Senken Temperatur ({target_name})"' in de_translation_source
    assert '"Lüften: Senken Luftfeuchte ({target_name})"' in de_translation_source
    assert '"Lüften: Generisch ({target_name})"' in de_translation_source


def test_floor_sensor_selection_is_based_on_available_room_sensor_types() -> None:
    floor_kinds = determine_floor_sensor_kinds(
        [
            RoomSensorKinds(temperature=True, humidity=False, generic=True),
            RoomSensorKinds(temperature=False, humidity=True, generic=True),
        ],
        include_generic=True,
    )

    assert floor_kinds == RoomSensorKinds(temperature=True, humidity=True, generic=True)


def test_select_first_available_entity_uses_precedence() -> None:
    selected = select_first_available_entity(
        ["sensor.floor_temp", "sensor.global_temp", "sensor.auto_temp"],
        is_available=lambda entity_id: entity_id in {"sensor.global_temp", "sensor.auto_temp"},
    )

    assert selected == "sensor.global_temp"


def test_select_first_available_entity_returns_none_when_unavailable() -> None:
    selected = select_first_available_entity(
        ["sensor.floor_temp"],
        is_available=lambda entity_id: entity_id == "sensor.some_other_entity",
    )

    assert selected is None


def test_outdoor_source_resolution_falls_back_floor_global_auto() -> None:
    resolved_temperature, resolved_humidity = resolve_outdoor_source_entities(
        floor_temperature_entity_id="sensor.floor_temp",
        global_temperature_entity_id="sensor.global_temp",
        auto_temperature_entity_id="sensor.auto_temp",
        floor_humidity_entity_id="sensor.floor_humidity",
        global_humidity_entity_id="sensor.global_humidity",
        auto_humidity_entity_id="sensor.auto_humidity",
        is_available=lambda entity_id: entity_id
        in {
            "sensor.global_temp",
            "sensor.floor_humidity",
            "sensor.auto_temp",
            "sensor.auto_humidity",
        },
    )

    assert resolved_temperature == "sensor.global_temp"
    assert resolved_humidity == "sensor.floor_humidity"


def test_outdoor_source_resolution_uses_auto_when_floor_and_global_unavailable() -> None:
    resolved_temperature, resolved_humidity = resolve_outdoor_source_entities(
        floor_temperature_entity_id="sensor.floor_temp",
        global_temperature_entity_id="sensor.global_temp",
        auto_temperature_entity_id="sensor.auto_temp",
        floor_humidity_entity_id="sensor.floor_humidity",
        global_humidity_entity_id="sensor.global_humidity",
        auto_humidity_entity_id="sensor.auto_humidity",
        is_available=lambda entity_id: entity_id
        in {
            "sensor.auto_temp",
            "sensor.auto_humidity",
        },
    )

    assert resolved_temperature == "sensor.auto_temp"
    assert resolved_humidity == "sensor.auto_humidity"


def test_room_threshold_override_uses_defaults_for_invalid_values() -> None:
    room_overrides = {
        "living_room": {
            "temperature_delta_c": "2.5",
            "humidity_delta_gm3": -1.0,
        }
    }

    temperature_delta_c, humidity_delta_gm3 = resolve_room_threshold_values(
        room_overrides,
        "living_room",
        default_temperature_delta_c=1.0,
        default_humidity_delta_gm3=1.0,
        temperature_key="temperature_delta_c",
        humidity_key="humidity_delta_gm3",
    )

    assert temperature_delta_c == 2.5
    assert humidity_delta_gm3 == 1.0


def test_room_outdoor_override_precedence_prefers_room_before_floor_global_auto() -> None:
    selected = select_first_available_entity(
        [
            "sensor.room_outdoor_temperature",
            "sensor.floor_outdoor_temperature",
            "sensor.global_outdoor_temperature",
            "sensor.auto_outdoor_temperature",
        ],
        is_available=lambda entity_id: entity_id
        in {
            "sensor.room_outdoor_temperature",
            "sensor.floor_outdoor_temperature",
            "sensor.global_outdoor_temperature",
            "sensor.auto_outdoor_temperature",
        },
    )

    assert selected == "sensor.room_outdoor_temperature"


def test_room_outdoor_override_falls_back_to_floor_if_room_unavailable() -> None:
    selected = select_first_available_entity(
        [
            "sensor.room_outdoor_temperature",
            "sensor.floor_outdoor_temperature",
            "sensor.global_outdoor_temperature",
            "sensor.auto_outdoor_temperature",
        ],
        is_available=lambda entity_id: entity_id
        in {
            "sensor.floor_outdoor_temperature",
            "sensor.global_outdoor_temperature",
            "sensor.auto_outdoor_temperature",
        },
    )

    assert selected == "sensor.floor_outdoor_temperature"
