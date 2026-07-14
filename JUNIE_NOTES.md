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
