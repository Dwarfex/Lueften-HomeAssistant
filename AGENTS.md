# AGENTS Guide

This file aligns autonomous agents working in this repository.

## Project Context

- Product intent and user-facing behavior: `README.md`
- Active feature specifications: `Features/`
- Technical task specs per feature: `Features/*_tasks/`
- Instruction/correction log for agent behavior: `JUNIE_NOTES.md`

## Workflow Rules

1. Follow spec-driven development.
2. For each new feature:
   - Ask 5–10 product clarification questions.
   - Finalize a timestamped feature file in `Features/`.
   - Assign a semantic version tag to the feature spec (for GitHub release traceability).
   - Create timestamped technical task instructions in that feature’s `_tasks` folder.
   - Ask 3 technical clarification questions before implementation.
3. Newer feature decisions override older feature decisions.
4. Keep feature/task filenames timestamped (`YYYY-MM-DD_HH-MM`).

## Implementation & Validation

- Home Assistant integration target: HACS custom integration (`custom_components/lueften`).
- Run tests in Docker only.
- Prefer Make targets for verification:
  - `make test`
  - `make test-docker`
  - `make test-docker-verbose`

## Agent Compatibility Notes

- Before coding, read the latest finalized feature and task files.
- If instructions evolve, append updates to `JUNIE_NOTES.md` so future agents stay consistent.
