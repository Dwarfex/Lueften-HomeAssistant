# Feature Spec — Setup Dropdowns & Deferred Outdoor Overrides

- Created: `2026-07-14_17-48`
- Status: `Finalized`
- Priority: `Highest (newest feature decisions override older ones)`
- Semantic Version Tag: `v0.2.0`

## 1) Goal

Improve setup/options UX so users do not need to manually type default outdoor entity IDs and do not need to edit JSON for outdoor override mappings.

## 2) Product Decisions (resolved)

1. Initial setup outdoor temperature is mandatory.
2. Initial setup outdoor humidity is optional with auto-discovery fallback.
3. Dropdown candidates must include only sensor entities with matching device class.
4. Dropdown rendering should show friendly name plus entity ID (Home Assistant entity selector behavior).
5. Per-sensor outdoor overrides are configured in options flow only.
6. Per-sensor override configuration should be available after successful discovery.
7. Override persistence remains in config entry options.
8. If a selected override entity is no longer available, surface a configuration error in options handling.

## 3) Scope

- Setup flow:
  - Replace manual outdoor entity ID text fields with dropdown selectors.
  - Keep temperature required and humidity optional.
- Options flow:
  - Remove manual JSON entry for floor outdoor overrides from user-facing form.
  - Add a dedicated room/sensor override configuration step based on discovered rooms.
- Runtime:
  - Apply room-level outdoor override precedence before floor/global/auto fallback.

## 4) Compatibility Notes

- Existing stored mappings remain normalized through option merge logic.
- New behavior extends precedence to room-level overrides while preserving existing fallback chain.
