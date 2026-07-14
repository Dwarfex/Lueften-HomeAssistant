# Junie Instruction & Correction Notes

## 2026-07-14 15:21

- Work in spec-driven-development mode.
- Keep feature specs in `Features/`.
- For each new feature: ask 5-10 clarification questions before finalizing the feature spec.
- For each feature: create technical task instructions and ask 3 technical clarification questions before full implementation.
- Newer feature decisions override older feature decisions.
- Mark feature/task artifacts with creation date and time in file names.

## 2026-07-14 15:48

- Run tests in Docker.
- Provide a `Makefile` to run test commands easily.

## 2026-07-14 15:55

- Add a project `AGENTS.md` for cross-agent compatibility and shared workflow context.

## 2026-07-14 15:57

- Add `.gitignore`.
- Keep local paths out of committed code and prefer project-relative/path-derived references.

## 2026-07-14 15:52

- Each feature gets a semantic version tag for release traceability.

## 2026-07-14 17:50

- Setup/Options UX decision: use entity dropdown selectors for outdoor temperature/humidity instead of manual entity-id typing.
- Outdoor temperature selection is mandatory in setup; outdoor humidity stays optional with fallback.
- Outdoor override configuration should be handled via options flow after discovery, not via manual JSON editing.

## 2026-07-14 19:33

- Release notes language policy: all existing and future GitHub release notes must be written in English.

## 2026-07-14 19:45

- For every bugfix, explicitly assess upgrade impact for already-installed versions and add a migration fix whenever required.

## 2026-07-14 19:55

- Keep `custom_components/lueften/manifest.json` version aligned with every published Git tag/release version (always).

## 2026-07-14 20:00

- Maintain a release GitHub Action guard that fails when release tag version and `manifest.json` version diverge.
