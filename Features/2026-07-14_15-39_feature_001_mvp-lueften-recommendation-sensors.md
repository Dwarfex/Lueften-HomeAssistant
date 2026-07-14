# Feature Spec — MVP Lüften Recommendation Sensors

- Created: `2026-07-14_15-39`
- Status: `Finalized`
- Priority: `Highest (newest feature decisions override older ones)`
- Semantic Version Tag: `v0.1.0`

## 1) MVP Feature List Extracted from README

1. Auto-detect applicable rooms and floors.
2. Create room-level Lüften recommendation binary sensors.
3. Create floor-level aggregated Lüften recommendation binary sensors.
4. Support temperature-based recommendation logic.
5. Support absolute-humidity-based recommendation logic.
6. Support configurable sensor creation per type.
7. Support floor threshold configuration for floor-level recommendation.

## 2) First Feature Scope (Cycle 1)

Implement the full MVP sensor package in one cycle:

- Room-level recommendation sensors for:
  - `Lüften to reduce temperature`
  - `Lüften to reduce absolute humidity`
- Floor-level recommendation sensors for:
  - `Lüften to reduce temperature`
  - `Lüften to reduce absolute humidity`
- Generic recommendation sensors for:
  - `Should Lüften` (room)
  - `Should Lüften` (floor)
- Event-driven recalculation (state-change driven).
- English labels/entity naming.
- Outdoor source behavior:
  - Auto-discover defaults.
  - Allow user overrides (including per-floor override requirement from clarification).
- Missing input behavior:
  - Default skip for rooms without required sensors.
  - Regular rescans for newly added matching entities.
- Default thresholds (configurable per room):
  - Temperature recommendation: indoor is at least `1°C` hotter than reference.
  - Humidity recommendation: outdoor is at least `1 g/m³` drier than indoor.
- Floor aggregation: per sensor type, floor sensor is `on` when at least `N` rooms of the same type are `on` (`N=1` default).
- Air-quality support: not implemented in MVP logic; keep architecture/configuration extension-ready.

## 3) Clarification Answers Captured

- Scope: Full package.
- Condition types selected: temperature + humidity.
- Generic logic intent: configurable, with `any` as default; floor threshold notion mentioned.
- Outdoor source: auto-discovery + user overrides; mention of temperature/humidity/air-quality entity families.
- Missing inputs: skip/exclude by default, configurable, and periodic rescanning.
- Evaluation timing: state-event driven.
- Naming: English labels.
- Threshold defaults: `1°C` and `1 g/m³`, configurable per room.

## 4) Contradictions / Gaps Found

1. **Generic sensor inclusion ambiguity** — resolved: generic sensor is mandatory in this cycle.
2. **Floor aggregation rule ambiguity** — resolved: per-type threshold aggregation (default `1`).
3. **Air-quality mention scope ambiguity** — resolved: extension-ready only, no air-quality logic in this MVP.

## 5) Finalization Questions (to resolve before locking spec)

Resolved answers:

1. Generic Sensor Inclusion: `Include always`
2. Floor Aggregation Rule: `Per type threshold`
3. Air Quality Scope: `Prepare only`
