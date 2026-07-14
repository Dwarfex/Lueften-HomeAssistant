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


def test_floor_sensor_selection_is_based_on_available_room_sensor_types() -> None:
    floor_kinds = determine_floor_sensor_kinds(
        [
            RoomSensorKinds(temperature=True, humidity=False, generic=True),
            RoomSensorKinds(temperature=False, humidity=True, generic=True),
        ],
        include_generic=True,
    )

    assert floor_kinds == RoomSensorKinds(temperature=True, humidity=True, generic=True)
