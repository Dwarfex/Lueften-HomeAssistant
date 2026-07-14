from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite
from typing import Optional, Sequence


def _is_valid_number(value: object) -> bool:
    return isinstance(value, (int, float)) and isfinite(value)


def absolute_humidity_gm3(temperature_c: float, relative_humidity_pct: float) -> Optional[float]:
    """Compute absolute humidity in g/m³ from temperature and relative humidity.

    Formula uses saturation vapor pressure approximation (Magnus formula).
    """
    if not _is_valid_number(temperature_c) or not _is_valid_number(relative_humidity_pct):
        return None

    if relative_humidity_pct < 0 or relative_humidity_pct > 100:
        return None

    saturation_hpa = 6.112 * exp((17.67 * temperature_c) / (temperature_c + 243.5))
    vapor_pressure_hpa = (relative_humidity_pct / 100.0) * saturation_hpa
    return 216.7 * (vapor_pressure_hpa / (temperature_c + 273.15))


def should_lueften_for_temperature(
    indoor_temperature_c: float,
    outdoor_temperature_c: float,
    min_delta_c: float = 1.0,
) -> Optional[bool]:
    if not _is_valid_number(indoor_temperature_c) or not _is_valid_number(outdoor_temperature_c):
        return None

    if not _is_valid_number(min_delta_c) or min_delta_c < 0:
        return None

    return (indoor_temperature_c - outdoor_temperature_c) >= min_delta_c


def should_lueften_for_humidity(
    indoor_temperature_c: float,
    indoor_relative_humidity_pct: float,
    outdoor_temperature_c: float,
    outdoor_relative_humidity_pct: float,
    min_delta_gm3: float = 1.0,
) -> Optional[bool]:
    if not _is_valid_number(min_delta_gm3) or min_delta_gm3 < 0:
        return None

    indoor_abs = absolute_humidity_gm3(indoor_temperature_c, indoor_relative_humidity_pct)
    outdoor_abs = absolute_humidity_gm3(outdoor_temperature_c, outdoor_relative_humidity_pct)
    if indoor_abs is None or outdoor_abs is None:
        return None

    return (indoor_abs - outdoor_abs) >= min_delta_gm3


@dataclass(frozen=True)
class RoomInputs:
    indoor_temperature_c: Optional[float]
    indoor_relative_humidity_pct: Optional[float]
    outdoor_temperature_c: Optional[float]
    outdoor_relative_humidity_pct: Optional[float]
    enable_temperature: bool = True
    enable_humidity: bool = True
    include_generic: bool = True
    temperature_delta_c: float = 1.0
    humidity_delta_gm3: float = 1.0


@dataclass(frozen=True)
class RoomRecommendation:
    temperature: Optional[bool]
    humidity: Optional[bool]
    generic: Optional[bool]


def build_room_recommendation(inputs: RoomInputs) -> RoomRecommendation:
    temperature: Optional[bool] = None
    humidity: Optional[bool] = None

    if inputs.enable_temperature:
        temperature = should_lueften_for_temperature(
            indoor_temperature_c=inputs.indoor_temperature_c,
            outdoor_temperature_c=inputs.outdoor_temperature_c,
            min_delta_c=inputs.temperature_delta_c,
        )

    if inputs.enable_humidity:
        humidity = should_lueften_for_humidity(
            indoor_temperature_c=inputs.indoor_temperature_c,
            indoor_relative_humidity_pct=inputs.indoor_relative_humidity_pct,
            outdoor_temperature_c=inputs.outdoor_temperature_c,
            outdoor_relative_humidity_pct=inputs.outdoor_relative_humidity_pct,
            min_delta_gm3=inputs.humidity_delta_gm3,
        )

    generic: Optional[bool] = None
    if inputs.include_generic:
        candidates = [condition for condition in (temperature, humidity) if condition is not None]
        generic = any(candidates) if candidates else None

    return RoomRecommendation(temperature=temperature, humidity=humidity, generic=generic)


def _aggregate_condition(values: Sequence[Optional[bool]], threshold: int) -> Optional[bool]:
    if threshold < 1:
        raise ValueError("threshold must be >= 1")

    eligible_values = [value for value in values if value is not None]
    if not eligible_values:
        return None

    return sum(1 for value in eligible_values if value) >= threshold


@dataclass(frozen=True)
class FloorThresholds:
    temperature: int = 1
    humidity: int = 1
    generic: int = 1


def aggregate_floor_recommendations(
    room_recommendations: Sequence[RoomRecommendation],
    thresholds: FloorThresholds,
) -> RoomRecommendation:
    return RoomRecommendation(
        temperature=_aggregate_condition(
            [room.temperature for room in room_recommendations],
            thresholds.temperature,
        ),
        humidity=_aggregate_condition(
            [room.humidity for room in room_recommendations],
            thresholds.humidity,
        ),
        generic=_aggregate_condition(
            [room.generic for room in room_recommendations],
            thresholds.generic,
        ),
    )
