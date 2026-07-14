from __future__ import annotations

from collections.abc import Iterable, Mapping

DEVICE_CLASS_TEMPERATURE = "temperature"
DEVICE_CLASS_HUMIDITY = "humidity"


def _normalize_device_class(value: object) -> str:
    return str(value or "").strip().lower()


def discover_outdoor_candidates(
    entity_ids: Iterable[str],
    registry_device_classes: Mapping[str, object],
    state_device_classes: Mapping[str, object],
) -> tuple[list[str], list[str]]:
    temperature_candidates: list[str] = []
    humidity_candidates: list[str] = []

    for entity_id in sorted(set(entity_ids)):
        device_class = _normalize_device_class(registry_device_classes.get(entity_id))
        if not device_class:
            device_class = _normalize_device_class(state_device_classes.get(entity_id))

        if device_class == DEVICE_CLASS_TEMPERATURE:
            temperature_candidates.append(entity_id)
        elif device_class == DEVICE_CLASS_HUMIDITY:
            humidity_candidates.append(entity_id)

    return temperature_candidates, humidity_candidates
