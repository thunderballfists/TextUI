# Authoring Specification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Deliver issue #96 PR 3: generated authoring artifacts and nonexecuting static checks.

**Architecture:** Reuse ProjectSource discovery/lowering for static checks. Generate documents, completion data and two bounded XSD profiles from registry descriptions and packaged authoring facts. Keep runtime behavior unchanged.

**Tech Stack:** Python >=3.11, Textual 8, lxml XMLSchema, pytest; existing locked dependencies only.

**Spec:** `docs/superpowers/specs/2026-10-05-authoring-spec-design.md`

## Global Constraints

- No runtime markup changes, dependency/version changes, publishing or credentials.
- Static checking never imports linked controllers, constructs widgets or invokes lifecycle hooks.
- Use `uvx --python 3.12 --from poetry==2.4.3 poetry` for project commands.
- Preserve ordinary trusted check behavior, locations and exit codes.
- Canonical schema limitations and permissive authoring profile must be explicit.

## Review Focus

- Included file errors retain source attribution rather than the entry path (Task 1).
- Component-private IDs and format placeholders remain compatible (Tasks 1/3).
- Arbitrary dynamic aliases require static resolution, not misleading XSD approval (Task 3).
- Completion and generation work with no checkout and no optional image dependencies (Task 4).
- JSON stdout stays machine-readable on expected parse/file failures (Task 1).

### Task 1: Nonexecuting static checking

**Files:** `textui/static_check.py`, `textui/__main__.py`, `tests/test_static_check.py`.

**Interfaces:** Consumes `ProjectSource.discover(path).lower(default_component_registry())`; produces `check_static(path: str | Path) -> Document` and `diagnostic(error: TextUIError, path: str | Path) -> dict[str, object]`.

- [ ] Write tests for static CLI success, exact JSON diagnostic fields, includes/components, nonexecuting script and App/Widget sentinels, static split/nav checks, existing check and argument errors.
- [ ] Run `poetry run python -m pytest tests/test_static_check.py -q`; expected missing feature failures.
- [ ] Implement pure discovery/lowering and metadata-derived canonical native-child checks; add CLI flags with JSON allowed only for static mode.
- [ ] Run `poetry run python -m pytest tests/test_static_check.py tests/test_project_cli.py tests/test_project_check.py -q`; expected all pass.
- [ ] Commit `Add nonexecuting static project checks`.

### Task 2: Registry-derived artifacts

**Files:** `textui/authoring/` modules and packaged samples, `tests/test_authoring.py`, generated artifacts; CLI spec subcommand.

**Interfaces:** Consumes `default_component_registry().describe()`; produces `artifacts() -> dict[str, str]` and `write_spec(output: str | Path) -> tuple[Path, ...]`. All outputs independent of checkout paths/time.

- [ ] Write tests requiring all seven artifacts, deterministic bytes, every tag/attribute/event, canonical sample parity, noninvocation of factories, and installed-style CLI generation into arbitrary directories.
- [ ] Run `poetry run python -m pytest tests/test_authoring.py -q`; expected missing generator failures.
- [ ] Implement focused reference/completion/schema generators and packaged authoring facts; generate committed outputs.
- [ ] Run `poetry run python -m pytest tests/test_authoring.py tests/test_static_check.py -q`; expected all pass.
- [ ] Commit `Generate registry-derived authoring artifacts`.

### Task 3: Schema and guidance corpus

**Files:** `tests/test_authoring_schema.py`, explicit schema exception fixtures, reference generators as required.

**Interfaces:** Consumes Task 2 artifacts and Task 1 checks; produces executable agreement corpus and documented schema limits.

- [ ] Add loader/XSD agreement tests for structural fixtures; exact allowlist for non-schema rules. Add raw authoring and expanded strict validation for every example, complete README/LLM examples, and common mistake rejection tests.
- [ ] Run `poetry run python -m pytest tests/test_authoring_schema.py -q`; expected unsupported schema/guidance case failures.
- [ ] Correct schema generation only where consistent with unchanged runtime semantics; document intentional limits and test dynamic aliases/placeholders.
- [ ] Run `poetry run python -m pytest tests/test_authoring_schema.py tests/test_authoring.py tests/test_static_check.py -q`; expected all pass.
- [ ] Commit `Verify schema agreement and authoring examples`.

### Task 4: Documentation and installed-wheel delivery

**Files:** `docs/editors.md`, README, migration, roadmap, changelog, `pyproject.toml`, `tests/wheel_smoke.py`.

**Interfaces:** Consumes completed CLI/artifacts; produces wheel/sdist verification and linked user guidance.

- [ ] Extend wheel smoke assertions to exercise generation and static checks outside a checkout, without controller execution.
- [ ] Add editor associations and limits, CLI examples, migration guidance, roadmap 1C delivered and changelog Added entries. Include root artifacts in sdist.
- [ ] Run full `poetry run python -m pytest -q`, opt-in visual tests, Pyflakes, `poetry check --lock`, `poetry build`, and clean-wheel `python -I tests/wheel_smoke.py` following CI's environment procedure; expected green with no optional image packages.
- [ ] Commit `Document and verify installed authoring tools`.
- [ ] Fresh whole-branch review; fix important findings with regression tests; create PR, inspect CI and bot feedback, integrate only when checks pass, and verify main afterward.
