# Project Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run an HTML-like `.ui` project with local includes, linked styles and Python, lifecycle hooks, actions, and timers.

**Architecture:** A resource-discovery pass builds an expanded source tree without executing Python. A `ProjectApp` loads controller modules in its Textual load phase, allows setup to extend the registry, lowers the tree into the existing `Document`, and binds it before composition. Textual owns rendering, scheduling, workers, and shutdown.

**Tech Stack:** Python 3.11+, lxml 6, Textual 8, pytest/pytest-asyncio, Poetry.

**Spec:** `docs/superpowers/specs/2026-09-18-textui-project-runtime-design.md`

## Global Constraints

- Preserve `DocumentLoader`, `Document.bind`, and `TextUI(Document, actions=...)`.
- Only local UTF-8 resources; no inline Python, networking, globs, reload, or custom scheduler.
- Controllers are trusted code and execute once per App binding in distinct namespaces.
- Preserve source filename and line in diagnostics; reserve `ui`, `style`, `script`, and `include`.

---

### Task 1: Discover and lower project resources

**Files:** Create `textui/project.py`, `tests/test_project.py`; modify `textui/loader.py`, `textui/registry.py` as needed.

**Interfaces:** Produce `ProjectSource.discover(path: str | Path) -> ProjectSource` and `ProjectSource.lower(registry: ComponentRegistry) -> Document`; expose ordered `scripts: tuple[Path, ...]`. Reuse the loader's strict XML parser, conversion, and validation; do not import Python here.

- [ ] **Step 1: Write a failing test.** Use `tmp_path` to create `app.ui` with `<include src="views/child.ui"/>`, a nested include, `<style src="shell.tcss"/>`, and `<script src="controller.py"/>`; assert the resulting document has included nodes, style source path, and ordered script paths. Add rejection cases for cycles, missing files, duplicate IDs, style/script inside includes, invalid attributes/text, and child-policy violations.
- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_project.py -q`; expect import/API failures.
- [ ] **Step 3: Implement** an expanded node wrapper carrying original `SourceLocation`; resolve each relative path against its declaring file; canonicalize paths for cycle detection; lower only after a registry is supplied. Ensure styles retain document order and IDs are checked globally.
- [ ] **Step 4: Run** `.venv/bin/python -m pytest tests/test_project.py tests/test_loader.py -q`; expect pass.
- [ ] **Step 5: Commit** resource discovery, lowering, and tests.

### Task 2: Link controller modules and lifecycle

**Files:** Create `textui/controllers.py`, `textui/project_app.py`, `tests/test_project_app.py`; modify `textui/__init__.py`, `textui/errors.py`, `textui/textui.py` if event forwarding is shared.

**Interfaces:** Produce `action(function)` marker, `ProjectApp(source: ProjectSource, *, actions: Mapping[str, ActionCallback] | None = None)`, and `ProjectWindow` with `app`, `registry`, and phase-checked `document`. Load source files in isolated module namespaces with `window` injected. `on_setup/on_ready/on_close` accept zero arguments, sync or async.

- [ ] **Step 1: Write failing Pilot tests** for setup-time registration, zero/one-context decorated actions, undisclosed functions, duplicate exports, module ordering, independent App state, document lookup after ready, and close after startup failure.
- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_project_app.py -q`; expect API failures.
- [ ] **Step 3: Implement** module execution during `on_load`, signature validation, hook invocation, lowering and binding before `compose`, and ready/close hooks in native lifecycle. Wrap failures with controller path and function name.
- [ ] **Step 4: Run** `.venv/bin/python -m pytest tests/test_project_app.py tests/test_actions.py -q`; expect pass.
- [ ] **Step 5: Commit** controllers, App integration, and tests.

### Task 3: Timers and worker ownership

**Files:** Create `textui/timers.py`, `tests/test_project_timers.py`; modify `textui/controllers.py`, `textui/project_app.py`, `textui/__init__.py`.

**Interfaces:** Produce `every(seconds: float, *, thread: bool = False)` decorator and `window.after(seconds, callback)`, `window.every(seconds, callback, *, thread=False)`, `window.call_ui(callback, *args, **kwargs)`. Return Textual `Timer` handles; callbacks accept no arguments.

- [ ] **Step 1: Write failing Pilot tests** for positive finite intervals, one-shot and periodic firing, async callbacks that leave the message queue responsive, non-overlapping repeats, explicit thread marshaling, timer handles, and shutdown cancellation.
- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_project_timers.py -q`; expect API failures.
- [ ] **Step 3: Implement** Textual `set_timer`/`set_interval` wrappers, worker ownership, in-flight skip behavior, and close cleanup. Start decorated timers only after `on_ready` succeeds.
- [ ] **Step 4: Run** `.venv/bin/python -m pytest tests/test_project_timers.py -q`; expect pass.
- [ ] **Step 5: Commit** timers and tests.

### Task 4: Command and installable example

**Files:** Create `textui/__main__.py`, `examples/project/app.ui`, `examples/project/controller.py`, `examples/project/shell.tcss`, `tests/test_project_cli.py`; modify `pyproject.toml`, `README.md`, `docs/` guide and `CHANGELOG.md`.

**Interfaces:** `textui run path/to/app.ui` invokes `ProjectSource.discover` and `ProjectApp.run`; `python -m textui run ...` also works.

- [ ] **Step 1: Write a failing CLI test** for argument handling and loading the sample from another working directory; test installed wheel outside the checkout.
- [ ] **Step 2: Run** `.venv/bin/python -m pytest tests/test_project_cli.py -q`; expect failure.
- [ ] **Step 3: Implement** console script, example, and focused authoring documentation, including trusted Python warning and API phase rules. Choose version after compatibility review; update lockfile if changed.
- [ ] **Step 4: Run** `.venv/bin/python -m pytest -q`, build the wheel, install it in a clean environment, and execute CLI from outside the checkout; expect pass.
- [ ] **Step 5: Commit** packaging, example, documentation, and tests.

## Self-Review

The four tasks cover resource grammar, source diagnostics, per-App execution, exports and hooks, timer semantics, CLI, documentation, and installability. All APIs are defined in the producing task. The workspace layout milestone has its own plan.
