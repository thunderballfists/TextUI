# Workspace Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add mouse-selectable navigation and a two-pane workspace that can be resized and hidden without losing the HTML-like markup model.

**Architecture:** Register a small set of typed components in the existing registry. Native Textual widgets own pointer capture, keyboard bindings, sizing, and events; TextUI's document binding dispatches the declared events to explicit actions.

**Tech Stack:** Python 3.11+, Textual 8, pytest/pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-09-18-textui-project-runtime-design.md`

## Global Constraints

- Keep `<split>` limited to exactly two `<pane>` children and `<nav>` limited to `<nav-item>` children.
- Use Textual `display` to hide panes and restore the prior share when shown.
- Keep included views static; do not add screens, modes, or arbitrary HTML.

---

### Task 1: Two-pane layout

**Files:** Create `textui/widgets/split.py`, `tests/test_split.py`; modify `textui/widgets/builtin_widgets.py`, `textui/loader.py` only if structural validation requires it.

**Interfaces:** Register `<split direction="horizontal|vertical">` with exactly two `<pane>` children. Each pane accepts minimum size; `Split` publishes resize and toggle messages. Its divider is internal and has no document ID.

- [x] **Step 1: Write failing tests** for grammar, initial sizing, drag, keyboard resize, minimum clamping, hide/show restoration, and terminal resize under Pilot.
- [x] **Step 2: Run** `.venv/bin/python -m pytest tests/test_split.py -q`; expect failure.
- [x] **Step 3: Implement** typed factories and a native Textual split widget with mouse capture, keyboard bindings, and size state. Reject malformed children before mounting.
- [x] **Step 4: Run** `.venv/bin/python -m pytest tests/test_split.py -q`; expect pass.
- [x] **Step 5: Commit** split component and tests.

### Task 2: Navigation and content switching

**Files:** Create `textui/widgets/navigation.py`, `tests/test_navigation.py`; modify `textui/widgets/builtin_widgets.py`, `textui/textui.py`, `textui/project_app.py`, and project example/docs.

**Interfaces:** Register `<nav>` and `<nav-item target="content-id">`; publish selection with the target; validate targets in the document before mount. An explicit action switches a native `ContentSwitcher`-style content area.

- [x] **Step 1: Write failing tests** for markup grammar, missing targets, mouse and keyboard selection, declared event dispatch, and content change.
- [x] **Step 2: Run** `.venv/bin/python -m pytest tests/test_navigation.py -q`; expect failure.
- [x] **Step 3: Implement** registry specs, event forwarding, target validation, and a sidebar example that calls the native content switcher through `window.document`.
- [x] **Step 4: Run** `.venv/bin/python -m pytest tests/test_navigation.py -q` and `.venv/bin/python -m pytest -q`; expect pass.
- [x] **Step 5: Commit** navigation and docs.

## Self-Review

The tasks cover layout grammar, pointer and keyboard control, hide/show, clamping, events, target validation, and a runnable sidebar example. The project runtime plan supplies linked resources and actions first.
