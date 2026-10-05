# Registry Metadata Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Describe existing attribute types and structural validation as inspectable registry data without changing runtime behavior.

**Architecture:** Frozen callable value types provide conversion and description. Ordered content constraints drive a generic structural checker, while named checks retain compound validation and construction-stage checks remain in construction. Explicit built-in declarations enrich immutable registrations and preserve native-factory matching.

**Tech Stack:** Python >=3.11, Textual 8.2.8, lxml, pytest/pytest-asyncio, isolated Poetry 2.4.3.

**Spec:** `docs/superpowers/specs/2026-10-05-registry-metadata-design.md`, implementing issue #96 PR 2.

## Global constraints

- Preserve accepted markup, values/defaults, diagnostic text and locations, validation order and phase.
- Preserve plain callable converters and custom tag/factory registrations.
- No dependency, version, import/CLI-name or imaging-boundary changes.
- Generate no schemas/reference artifacts and add no static-check command in this PR.

## Review focus

- Unicode alphanumeric accelerators retain `str.isalnum()` semantics.
- Native-factory aliases and unrelated factories using built-in tag spellings keep their current behavior.
- Combined-invalid documents preserve which diagnostic occurs first.
- Mutable description/default values cannot mutate metadata or another inspection.
- Invalid split/navigation children remain construction failures, including native widget-instance acceptance.

## Task 1: Attribute metadata

Files: `textui/metadata.py`, `textui/registry.py`, specialized built-in declarations; tests in `tests/test_registry_metadata.py`.

Interfaces: frozen callable `Text`, `Bool`, `Int`, `Enum`, `Pattern`, `IdRef`, `Number`; `AttributeSpec.describe() -> dict[str, object]`.

- [x] Write literal conversion/description tests, custom-converter nonexecution and isolation tests.
- [x] Run focused tests and confirm the missing description API fails.
- [x] Implement types and preserve legacy converter compatibility and exact error messages.
- [x] Verify focused tests and the unchanged registry/converter suite; commit.

## Task 2: Ordered structural metadata

Files: `textui/content.py`, `textui/widgets/metadata.py`, `textui/widgets/structure.py`, `textui/registry.py`, `textui/widgets/builtin_widgets.py`; tests/fixtures under `tests/`.

Interfaces: immutable content constraints with `describe()` and validation; `ComponentSpec.content`; `ComponentSpec.describe() -> dict[str, object]`; named compound-check records.

- [x] Capture baseline diagnostic fixtures from the unchanged loader, with expected exception class, message, attribute, value and location.
- [x] Write failing completeness and real custom-content validation tests, including the review-focus cases above.
- [x] Declare built-in content and specialized attribute metadata explicitly; replace simple structural checks with generic interpretation, preserving compound order and legacy factory fallback.
- [x] Verify diagnostic fixture parity, unchanged structural/runtime tests and metadata completeness; commit.

## Task 3: Document and verify installed delivery

Files: `docs/registry-metadata.md`, README, migration/changelog/testing/roadmap as relevant, `tests/wheel_smoke.py`.

- [x] Document exact APIs, custom-converter limitations, migrated/deferred rule inventory and future generator boundary.
- [x] Extend wheel smoke with built-in and custom metadata inspection.
- [x] Run full pytest, opt-in visual comparisons, Pyflakes, lock validation, builds and fresh wheel-only smoke.
- [x] Obtain independent review, implement verified feedback, and commit/push a PR linked to #96 without closing the remaining generator work.
- [ ] Verify Python 3.11/3.12/3.14 and Linux visual CI, address/resolve PR feedback, merge and verify the merged tree.
