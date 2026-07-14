# Technical Task Instructions — Feature 002 Setup Dropdowns & Deferred Overrides

- Created: `2026-07-14_17-49`
- Status: `Finalized`
- Source Feature: `../2026-07-14_17-48_feature_002_setup-dropdown-outdoor-overrides.md`

## Goal

Implement a user-friendly configuration UX for outdoor references:

- Setup uses dropdown selectors instead of manual entity-id text input.
- Outdoor temperature is required; outdoor humidity is optional.
- Per-room/per-sensor outdoor overrides are configured in options flow after discovery, without JSON editing.

## Implementation Outline

1. Add selector-based outdoor entity fields in setup/options base form.
2. Restrict candidate entities to sensor domain + matching device class.
3. Keep room threshold override JSON behavior unchanged for now.
4. Add options sub-step that renders discovered room-specific override fields.
5. Persist room override mapping in config entry options.
6. Extend runtime outdoor source precedence to room -> floor -> global -> auto.
7. Validate override entity existence when saving options and surface form error on invalid selection.
8. Keep normalization backward-compatible with existing stored options.

## Technical Clarification Questions

Resolved answers:

1. Storage model: `config entry options`
2. UI location for new per-sensor overrides: `options flow only`
3. Activation timing: `after successful discovery`
