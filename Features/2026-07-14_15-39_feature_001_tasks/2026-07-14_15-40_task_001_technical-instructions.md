# Technical Task Instructions — Feature 001 MVP Lüften Sensors

- Created: `2026-07-14_15-40`
- Status: `Finalized`
- Source Feature: `../2026-07-14_15-39_feature_001_mvp-lueften-recommendation-sensors.md`

## Goal

Implement Home Assistant integration logic that auto-discovers applicable rooms/floors and creates room/floor binary sensors for:

- `Should Lüften`
- `Lüften to reduce temperature`
- `Lüften to reduce absolute humidity`

with per-room configurable thresholds and per-type floor threshold aggregation.

## Implementation Outline

1. Create integration scaffolding for Home Assistant custom component (`lueften`) with config flow and options flow.
2. Implement entity discovery:
   - Discover floors and areas.
   - Discover relevant temperature/humidity entities per room.
   - Discover default outdoor references (with override capability).
3. Implement core calculation services:
   - Temperature recommendation calculation.
   - Absolute humidity conversion and comparison calculation.
   - Generic recommendation (`any` of enabled room conditions).
4. Implement room sensor entities.
5. Implement floor sensor entities using per-type threshold `N`.
6. Implement update orchestration:
   - Event-driven updates on source entity state changes.
   - Periodic rescan for newly added matching room entities.
7. Implement configuration model:
   - Enable/disable sensor types.
   - Global default thresholds (temperature/humidity).
   - Optional per-room threshold overrides.
   - Floor-level per-type threshold.
   - Outdoor entity override settings.
   - Triggerable rescan action from integration configuration/options.
8. Add test coverage for:
   - Calculation correctness and edge values.
   - Discovery/skip behavior when room data is incomplete.
   - Floor aggregation threshold behavior.
   - Generic sensor state behavior.

## Technical Clarification Questions

Resolved answers:

1. Packaging target: `HACS custom`
2. Config granularity: `Global defaults` (+ optional per-room overrides)
3. Rescan strategy: `Fixed interval` + `triggerable via plugin configuration`
