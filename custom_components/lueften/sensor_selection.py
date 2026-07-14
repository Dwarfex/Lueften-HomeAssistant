from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class RoomSensorKinds:
    temperature: bool
    humidity: bool
    generic: bool


def determine_room_sensor_kinds(
    *,
    has_indoor_temperature: bool,
    has_indoor_humidity: bool,
    enable_temperature: bool,
    enable_humidity: bool,
    include_generic: bool,
) -> RoomSensorKinds:
    temperature = enable_temperature and has_indoor_temperature
    humidity = enable_humidity and has_indoor_temperature and has_indoor_humidity
    generic = include_generic and (temperature or humidity)
    return RoomSensorKinds(temperature=temperature, humidity=humidity, generic=generic)


def determine_floor_sensor_kinds(
    room_kinds: Sequence[RoomSensorKinds],
    *,
    include_generic: bool,
) -> RoomSensorKinds:
    temperature = any(room.temperature for room in room_kinds)
    humidity = any(room.humidity for room in room_kinds)
    generic = include_generic and any(room.generic for room in room_kinds)
    return RoomSensorKinds(temperature=temperature, humidity=humidity, generic=generic)
