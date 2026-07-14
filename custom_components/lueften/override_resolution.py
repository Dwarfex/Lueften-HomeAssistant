from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any


def select_first_available_entity(
    candidates: Sequence[str | None],
    *,
    is_available: Callable[[str], bool],
) -> str | None:
    for candidate in candidates:
        if candidate and is_available(candidate):
            return candidate
    return None


def resolve_outdoor_source_entities(
    *,
    floor_temperature_entity_id: str | None,
    global_temperature_entity_id: str | None,
    auto_temperature_entity_id: str | None,
    floor_humidity_entity_id: str | None,
    global_humidity_entity_id: str | None,
    auto_humidity_entity_id: str | None,
    is_available: Callable[[str], bool],
) -> tuple[str | None, str | None]:
    return (
        select_first_available_entity(
            [
                floor_temperature_entity_id,
                global_temperature_entity_id,
                auto_temperature_entity_id,
            ],
            is_available=is_available,
        ),
        select_first_available_entity(
            [
                floor_humidity_entity_id,
                global_humidity_entity_id,
                auto_humidity_entity_id,
            ],
            is_available=is_available,
        ),
    )


def resolve_room_threshold_values(
    room_overrides: Mapping[str, Mapping[str, Any]],
    room_id: str,
    *,
    default_temperature_delta_c: float,
    default_humidity_delta_gm3: float,
    temperature_key: str,
    humidity_key: str,
) -> tuple[float, float]:
    override = room_overrides.get(room_id)
    if override is None:
        return default_temperature_delta_c, default_humidity_delta_gm3

    return (
        _as_non_negative_float(override.get(temperature_key), default_temperature_delta_c),
        _as_non_negative_float(override.get(humidity_key), default_humidity_delta_gm3),
    )


def _as_non_negative_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if parsed < 0.0:
        return default
    return parsed
