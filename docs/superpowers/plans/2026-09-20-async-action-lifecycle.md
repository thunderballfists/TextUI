# Async Action Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add opt-in target lifecycle state and supersession to async project actions.

**Architecture:** Decorator metadata declares a target ID and supersession policy. `BoundDocument` owns invocation tasks and updates only the active target invocation. `ActionContext` exposes the target and cancellation state without changing legacy actions.

**Tech Stack:** Python 3.11+, Textual, pytest, pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-09-20-async-action-lifecycle-design.md`

## Global Constraints

- Existing actions retain current behavior unless lifecycle metadata is declared.
- Cancellation clears loading state and is not reported as an error.
- Target IDs must be declared document IDs.

## Review Focus

- A replacement action must never clear the replacement’s loading class.
- Shutdown must cancel owned tasks and clear loading classes.
- A failed active action must retain its source location and target error text.
- Legacy synchronous and asynchronous actions retain their existing dispatch contract.
- An unknown lifecycle target fails before widget composition.

### Task 1: Lifecycle metadata and context

**Files:** `textui/actions.py`, `textui/controllers.py`, `tests/test_project_app.py`

- [ ] Add failing decorator tests for `target` and `supersede` metadata, including an unknown target validation failure.
- [ ] Extend action and command metadata with `target: str | None` and `supersede: bool`; validate identifier target names and pass metadata into `Document.bind`.
- [ ] Add `ActionContext.target` and `ActionContext.cancelled` accessors backed by one invocation state object.
- [ ] Run `pytest tests/test_project_app.py` and commit `Add lifecycle action metadata`.

### Task 2: Target task ownership and state

**Files:** `textui/document.py`, `tests/test_actions.py`

- [ ] Add failing tests where an async target action adds `-loading`, clears it after completion, and stores `textui_error` plus `-error` after failure.
- [ ] Add a task registry keyed by action name and target ID. Set lifecycle state before scheduling, clear it only when that task remains current, and route active failures through `ActionExecutionError`.
- [ ] Run `pytest tests/test_actions.py` and commit `Track lifecycle action state`.

### Task 3: Supersession and shutdown

**Files:** `textui/document.py`, `textui/project_app.py`, `tests/test_actions.py`, `tests/test_project_timers.py`

- [ ] Add failing tests where a superseding invocation cancels the earlier coroutine, preserves replacement loading state, and app exit cancels active lifecycle tasks.
- [ ] Cancel the prior registry task for `supersede=True`; add `BoundDocument.close()` and call it from project shutdown before controller close hooks.
- [ ] Run `pytest tests/test_actions.py tests/test_project_timers.py` and commit `Cancel superseded lifecycle actions`.

### Task 4: Documentation and verification

**Files:** `README.md`, `CHANGELOG.md`, tests above.

- [ ] Document lifecycle decorator options and target classes in the project-runtime section.
- [ ] Add an Unreleased changelog entry.
- [ ] Run `poetry run pytest`; run `pyflakes textui`; commit `Document async action lifecycle`.

## Self-review

Tasks cover metadata, active task ownership, stale completion, cancellation, shutdown, error context, legacy compatibility, documentation, and linting. The plan defines each new public interface before its consumers and contains no placeholder requirements.
