# Lüften

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Dwarfex&repository=Lueften-HomeAssistant&category=integration)

> **Lüften** *(noun)*: A uniquely German cultural ritual involving the simultaneous opening of every window in a building, usually during the least convenient weather imaginable, to combat the existential threat known as *stale air*. Failure to participate may result in judgment from nearby Germans.

**Lüften** brings this sacred German tradition to Home Assistant.

The integration analyzes your indoor climate and creates binary sensors that tell you **when you should air out a room or an entire floor** based on temperature and/or humidity.

## Features

- Automatically creates sensors for every room and floor that has the required climate sensors.
- Detect when airing out would reduce **temperature**.
- Detect when airing out would reduce **absolute humidity**.
- Provides a generic **"Should Lüften"** sensor that combines all enabled conditions.
- Aggregates room recommendations into floor-level recommendations.
- Configure exactly which sensor types should be created.

## Generated Sensors

Depending on your configuration, the integration can create the following binary sensors for each room:

- **Should Lüften** (generic)
- **Lüften to reduce temperature**
- **Lüften to reduce absolute humidity**

The generic **Should Lüften** sensor is `on` whenever **any enabled Lüften condition** for that room is `on`.

For each floor, the same sensor types can be created:

- **Should Lüften**
- **Lüften to reduce temperature**
- **Lüften to reduce absolute humidity**

Floor sensors aggregate the state of all rooms on that floor.
It also automatically discovers your Home Assistant **floors** and **areas (rooms)** and, by default, creates the generic **"Should Lüften"** binary sensors for each applicable room and floor.
## Configuration

The integration allows you to choose which sensor types should be created.

For example, you can enable only:

- Temperature-based Lüften sensors
- Humidity-based Lüften sensors
- Both

If a sensor type is disabled, it will not be created.

### Floor Threshold

You can define how many rooms on a floor must recommend Lüften before the floor-level sensor becomes `on`.

Default:

```yaml
floor_threshold: 1
```

This means that if **at least one room** recommends Lüften, the floor sensor will also recommend Lüften.

## Requirements

The integration automatically detects rooms and floors that contain supported sensors.

Depending on the enabled features, a room should provide:

- Air temperature sensor
- Relative humidity sensor

Rooms without the required sensors for a given feature are simply ignored.

## Installation

### HACS (Recommended)

1. Open **HACS**.
2. Navigate to **Integrations**.
3. Search for **Lüften**.
4. Install the integration.
5. Restart Home Assistant.
6. Add the integration from **Settings → Devices & Services**.

## Philosophy

Lüften doesn't try to automate your windows.

It simply tells you, with stereotypical German confidence, when it's time to open them.

