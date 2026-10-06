# Documentation Consolidation Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan inline, with a fresh whole-branch review before integration.

**Goal:** Complete roadmap Phase 1D by making current setup, reference, examples, migration and verification guidance easy to find.

**Architecture:** A documentation index directs readers to current guides and labels dated design records as historical evidence. The generated reference owns exhaustive markup facts; hand-written guides explain workflows and runtime boundaries.

**Tech Stack:** Markdown, existing Poetry 2.4.3 commands, pytest and distribution builds.

**Spec:** [Roadmap Phase 1D](../../roadmap.md#phase-1--developer-experience).

## Global Constraints

- Preserve existing AGENTS.md, historical plans/specs and unrelated root-checkout edits.
- Change documentation only; preserve runtime behavior, dependencies and version 0.7.0.
- Keep root README repository links absolute HTTPS for PyPI.
- Label authoring/metadata additions unreleased; do not tag or publish.
- Use Python 3.12 through isolated Poetry 2.4.3 and the documented cached-environment policy.

## Review Focus

- A PyPI 0.7.0 user must not mistake unreleased authoring commands for installed functionality.
- A checkout with an old .venv must follow setup without assuming its console script exists.
- A custom host must explicitly forward its actual message types and close its binding.
- Raw component/include projects must not be promised strict-XSD or complete static validation.
- Historical six-widget designs must not be presented as the current catalog.

### Task 1: Consolidate current documentation

**Files:** Create `docs/README.md`; modify `README.md`, `examples/README.md`, `docs/migration.md`, `docs/project-runtime.md`, `docs/testing.md`, `docs/releases.md`, `docs/roadmap.md`.

**Interfaces:** Consume existing runtime and generated-reference behavior; produce current guide navigation and reproducible contributor commands.

- [x] Add the current/historical documentation index and link it from README; replace its manual exhaustive widget table with generated-reference navigation and compact family overview.
- [x] Reconcile migration history with current forwarding/lifecycle rules; clarify the authoring release boundary in runtime guidance.
- [x] Catalog every example with its entry path and purpose; correct baseline/test distinctions and add generation/installed-wheel verification to testing/release guidance.
- [x] Record Phase 1D delivery in the roadmap without claiming unfinished compatibility work.
- [x] Verify local documentation paths/anchors, absolute README links, all example static/trusted checks, artifact generation parity, the complete headless suite, lock consistency and built distribution contents. Expected: no broken current-guide links, no artifact drift, successful checks/build and 669 passing tests.
- [x] Commit the documentation changes with an imperative summary.

## Integration

Obtain a fresh whole-branch review, address substantive findings, create a PR and inspect GitHub feedback. Merge only after the full test/build/wheel matrix, lint and Linux visual checks pass. Verify the resulting main tree, post-merge CI and late feedback. No application behavior changes require new regression tests; use existing behavioral and generated-artifact checks plus direct documentation verification.
