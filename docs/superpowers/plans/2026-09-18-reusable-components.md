# Reusable Components Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicitly imported reusable `.ui` components with string props, named/default slots, and instance-local IDs.

**Architecture:** Project discovery will parse component imports and expand instances into ordinary XML before `DocumentLoader` lowers markup. A focused `components.py` module owns parsing, property replacement, slots, IDs, and cycle errors; existing registry, styles, events, and document binding remain unchanged.

**Tech Stack:** Python 3.11+, lxml, Textual 8.x, pytest, pytest-asyncio, Poetry.

**Spec:** `docs/superpowers/specs/2026-09-18-reusable-components-design.md`

## Global Constraints

- Components are local UTF-8 files; no embedded Python, expression evaluation, component scripts, or component-local styles.
- Properties are strings and substitute only exact `{property}` tokens in text and attribute values.
- Public caller IDs remain document IDs; template IDs are instance-local and unavailable through `window.document.get_by_id`.
- Validate malformed roots, paths, imports, props, placeholders, slots, duplicate public IDs, and cycles with source context.

---

### Task 1: Component catalog and source validation

**Files:** Create `textui/components.py`; modify `textui/project.py`; test `tests/test_components.py`.

- [ ] Write failing tests for `<component src="cards/agent.ui" as="agent-card"/>`, duplicate aliases, non-local/missing paths, invalid component roots, and directives outside the entry root.
- [ ] Run `poetry run pytest tests/test_components.py -q`; expect import directives to fail as unknown markup.
- [ ] Implement `ComponentTemplate` and `ComponentCatalog.load_import(src: Path, alias: str, location: SourceLocation)`, reusing strict parser and local-path checks from `ProjectSource`.
- [ ] Run `poetry run pytest tests/test_components.py -q`; expect catalog tests to pass.
- [ ] Commit with `git commit -am "Parse reusable component imports"`.

### Task 2: Property expansion

**Files:** Modify `textui/components.py`, `textui/project.py`; test `tests/test_components.py`.

- [ ] Write failing tests using `<props><prop name="name" required="true"/><prop name="tone" default="plain"/></props>` and `{name}` in a label and `{tone}` in a class.
- [ ] Add cases for missing required props, undeclared props, malformed placeholders, and defaults.
- [ ] Implement `ComponentCatalog.expand(root, sources)` using deep copies; allow one widget root after optional `<props>`, apply caller common attributes to that root, and replace exact declared placeholders only.
- [ ] Run `poetry run pytest tests/test_components.py -q` and commit `Expand component properties`.

### Task 3: Default and named slots

**Files:** Modify `textui/components.py`; test `tests/test_components.py`.

- [ ] Write failing tests for `<slot name="actions">fallback</slot>`, unnamed default slots, caller replacement, fallback preservation, unknown slots, duplicate slots, and event-bearing slot buttons.
- [ ] Implement slot collection/replacement: caller children must be named `<slot>` declarations unless the template has one unnamed slot; replace placeholders with supplied children or copied fallback children.
- [ ] Run `poetry run pytest tests/test_components.py -q` and commit `Expand component slots`.

### Task 4: Local IDs and nested components

**Files:** Modify `textui/components.py`, `textui/project.py`; test `tests/test_components.py`, `tests/test_project.py`.

- [ ] Write failing tests for two `<agent-card>` instances each containing template `id="status"`, nested component use, and an import cycle reporting both paths.
- [ ] Rewrite template IDs with a deterministic `__component_<counter>_` prefix before ordinary validation; preserve the caller ID on the expanded root; maintain ancestry during recursive expansion.
- [ ] Run `poetry run pytest tests/test_components.py tests/test_project.py -q` and commit `Isolate component instances`.

### Task 5: Example, docs, and release validation

**Files:** Create `examples/components/{app.ui,controller.py,components/agent-card.ui,components.tcss}`; modify `README.md`, `docs/project-runtime.md`, `docs/migration.md`, `examples/README.md`, `CHANGELOG.md`, `tests/test_examples.py`.

- [ ] Write a failing example test that imports two cards and verifies a button provided through `actions` updates public `#feedback`.
- [ ] Add the runnable linked-controller example and document imports, props, slots, fallback content, local IDs, and intentionally deferred dynamic features.
- [ ] Run `poetry run pytest -q`, `uvx --from poetry==2.4.3 poetry check --lock`, and `uvx --from poetry==2.4.3 poetry build`.
- [ ] Inspect `git diff origin/main...HEAD --check`, commit documentation/verification changes, push, and open a PR.
