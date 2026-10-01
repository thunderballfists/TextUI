# Runtime Reliability Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` for inline execution and independent code review before integration. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Fix all five confirmed runtime reliability defects without changing markup or public decorator signatures.

**Architecture:** BoundDocument shares a private invocation owner across actions and commands. Timer ownership consumes native Worker terminal-state messages. Tables compare numeric values without float coercion.

**Tech Stack:** Python 3.11+, Textual 8, Poetry 2.4.3, pytest and pytest-asyncio.

**Spec:** [Runtime reliability design](../specs/2026-09-30-runtime-reliability-design.md).

**Completed:** 2026-09-30 in [PR #93](https://github.com/thunderballfists/TextUI/pull/93), merged at `9e5a464`. Validation: 431 headless tests, six unchanged visual comparisons, clean lint/lock/build checks, and passing Python 3.11/3.12/3.14 CI with clean-wheel verification. Independent review found no actionable issues; GitHub feedback was checked before and after merge.

## Global Constraints

- Python `>=3.11,<4`; Textual `>=8.2.8,<9`; lxml `>=6.1.3,<7`.
- Poetry 2.4.3; no added product dependencies or hand-edited lock resolutions.
- Strict XML, linked trusted Python, native TCSS and explicit custom-message forwarding remain unchanged.
- Core must not import or install Pillow or textual-imageview.
- Tests use headless Textual/Pilot and strict function-scoped asyncio loops; screenshots remain opt-in.
- Preserve exact registered message-type/source identity dispatch, immediate-error propagation, delayed-error reporting with source/cause, and native bubbling.
- Cancellation is cooperative. This work cannot force-stop a thread or prevent side effects from application code that deliberately suppresses cancellation.

## Review Focus

1. Closing immediately after a shortcut is scheduled must cancel the wrapper before a callback starts. Task 1 tests this separately from cancelling an already-started action.
2. An old superseded callback that catches cancellation and fails later must not overwrite newer target state. Task 1 verifies state and source-located error reporting separately.
3. Two different actions sharing a target must retain loading after either completes first. Task 1 tests both completion orders, including a command sharing the target.
4. A threaded worker may finish before ownership registration; it must still be released. Task 2 exercises fast async/threaded callbacks and late terminal messages.
5. Integers outside float range, NaN and mixed types must not break sorting or mutate a rejected replacement. Task 3 tests values and retained table state.

## Preparation and commands

At execution time, create `fix/runtime-reliability` in an isolated worktree using the worktree skill. Carry these committed planning files into it and preserve root untracked files, including the legacy `tests/test_markup.py`. Install the locked environment and run the clean worktree suite; the review baseline was 389 passing tests.

Every Poetry command below uses the full prefix:

```sh
uvx --python 3.12 --from poetry==2.4.3 poetry install --with test
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest -q
```

Execute Task 1 first. Tasks 2 and 3 share no new interfaces and can be developed independently afterward; integrate and verify one branch before opening the PR.

## Task 1 — Unify action and command lifecycle ownership (R1–R3)

**Files:** create `textui/invocations.py`; modify `textui/document.py`, `textui/project_app.py`, `textui/textui.py`; test `tests/test_actions.py`, `tests/test_project_app.py`; update `docs/project-runtime.md`, `README.md`, `CHANGELOG.md`.

**Interfaces:** private `OwnedInvocation` holds `state: ActionInvocation`. `InvocationOwner.begin(name: str, target: Widget | None, *, supersede: bool) -> OwnedInvocation`, `track(invocation: OwnedInvocation, task: asyncio.Future[object]) -> None`, `finish(invocation: OwnedInvocation, error: Exception | None = None) -> None`, `close() -> None`, and read-only `closed: bool`. BoundDocument still wraps errors and owns shortcut wrappers. Existing public dispatch/command/close signatures stay unchanged.

- [x] **Step 1: Write failing behavioral tests.** Reuse the normal Host binding pattern in `tests/test_actions.py` and `project()` helper in `tests/test_project_app.py`. Use Events to hold async work, not arbitrary sleeps. Cover the named cases and assertions below for actions and commands where applicable:

```python
# test_sync_target_action_and_command_complete_state
assert not status.has_class("-loading")
# test_sync_target_failure_sets_error_and_preserves_source
assert status.has_class("-error") and status.textui_error == "refresh failed"
assert error.value.__cause__ is original_error
# test_shared_target_keeps_loading_in_both_completion_orders
assert status.has_class("-loading")  # after one invocation finishes
# test_shutdown_cancels_untargeted_action_and_command
assert cancellation_seen.is_set() and post_close_effects == []
# test_close_before_shortcut_wrapper_starts
assert callback_calls == []
# test_closed_document_rejects_new_work
assert await bound.dispatch(message) is False
# invoke_command raises DocumentStateError; start_command creates no task.
# test_superseded_failure_does_not_overwrite_newer_target_state
assert not status.has_class("-error")  # newer generation succeeded
```

Also exercise repeated close, synchronous completion while another action owns the target, cancellation with no error indicator, native queued events during exit, and TextUI as well as ProjectApp cleanup. The superseded failure still reports a source-located ActionExecutionError through a capturing host error handler.

- [x] **Step 2: Run and record the expected failures.**

```sh
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/test_actions.py tests/test_project_app.py -q
```

Expected: new tests fail for retained untargeted tasks, sync loading, shared-target loading and absent close guards; existing regressions remain green.

- [x] **Step 3: Implement ownership and route both paths through it.** Use per-target active invocation sets/generations and separate `(name, target)` supersession keys. Begin before callback evaluation; finish sync results/errors directly and awaitable results through task completion. Make finishing idempotent. Track every callback task and shortcut wrapper. Close before App teardown; ignore later completion bookkeeping safely. Preserve immediate versus deferred exception handling and disabled commands.
- [x] **Step 4: Run focused tests and review the new lifecycle cases.** Use the command in Step 2. Expected: all focused tests pass, and none reports a cancelled task as an application error. Update runtime/host shutdown guidance and the Fixed changelog entries in the same change.
- [x] **Step 5: Commit only this deliverable.** Suggested summary: `Unify action ownership and shutdown cleanup`.

## Task 2 — Release finished timer workers (R4)

**Files:** modify `textui/timers.py`, `textui/project_app.py`; test `tests/test_project_timers.py`; update `CHANGELOG.md`.

**Interfaces:** retain `RuntimeTimers.schedule(...)` and returned native Timer handles. Add private `_own_worker(worker: Worker) -> None` and `handle_worker_state(event: Worker.StateChanged) -> None`; ProjectApp forwards native worker-state messages to its timer owner. Only Workers in the owned collection are handled.

- [x] **Step 1: Write failing async and threaded retention tests.** Schedule at least 20 completed ticks, stop the handle, then await native worker completion; assert the owned collection is empty. Use an Event/counter for completion. Also test fast completion, failed/cancelled workers, an unrelated host Worker, and late messages after repeated close:

```python
assert tick_count >= 20
assert all(worker.is_finished for worker in observed_workers)
assert app.window.timers.workers == set()
app.window.timers.close()
app.window.timers.close()
assert app.window.timers.handles == []
```

Capture worker references only in the test; production ownership must release them. Retain existing tests for skipped overlapping ticks and source-located timer failures.

- [x] **Step 2: Verify failure.**

```sh
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/test_project_timers.py -q
```

Expected: completed-worker retention and uncleared close collections fail.

- [x] **Step 3: Implement cleanup.** Add/check registration atomically on the UI side, including `worker.is_finished` after adding it. Remove owned workers on native SUCCESS/ERROR/CANCELLED messages without stopping normal error reporting. Stop handles and cancel workers using snapshots before clearing collections; tolerate late messages and preserve overlap skipping.
- [x] **Step 4: Run the command in Step 2.** Expected: all timer tests pass for async/threaded paths. Add a Fixed changelog entry.
- [x] **Step 5: Commit.** Suggested summary: `Release completed timer workers`.

## Task 3 — Preserve exact numeric table ordering (R5)

**Files:** modify `textui/widgets/data_widgets.py`; test `tests/test_data_widgets.py`; update `docs/controls.md`, `CHANGELOG.md`.

**Interfaces:** retain `set_rows(rows) -> None`, row lookup and header-click sorting. Change private `_sort_value(value: object) -> tuple[int, Real | str]` to preserve Real values; NaN falls through to text ordering. Preserve existing bool/numeric/text categories and stable ties.

- [x] **Step 1: Write failing header-interaction and refresh tests.** Supply larger-before-smaller rows, click the numeric heading, verify ascending then descending, and refresh with different records while sorting remains active:

```python
# test_runtime_table_sort_preserves_large_integer_precision
assert ordered_values == [2**53, 2**53 + 1]
# test_runtime_table_sort_handles_integers_outside_float_range
assert ordered_values == [10**400, 10**400 + 1]
# test_numeric_sort_policy_covers_mixed_values
# Ascending category policy for the supplied records:
assert ordered_values[:8] == [False, True, float("-inf"), 1, 1.5,
                              10**400, float("inf"), "alpha"]
assert ordered_values[8] is nan and ordered_values[9] is None
```

For the mixed test compare NaN by identity or `math.isnan`, never equality; textual ordering is `alpha`, `nan`, `None`. Also pin Decimal textual ordering, stable equal values, retained selected row keys, and rejected replacements leaving rows/cursor/sort direction unchanged.

- [x] **Step 2: Verify failures.**

```sh
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/test_data_widgets.py -q
```

Expected: adjacent large integers remain incorrectly ordered; huge integers overflow before the fix. NaN behavior is not deterministic under the old numeric key.

- [x] **Step 3: Implement exact keys and validate before mutation.** Avoid float conversion for Real values. Detect numeric NaN without converting large integers to float. Build sorted replacements before clearing rows or changing sort metadata. Keep header indicators, refresh sorting, cursor restoration and native seeded-string behavior intact.
- [x] **Step 4: Run the command in Step 2.** Expected: all table tests pass in both directions. Document the value categories and special-value policy, and add a Fixed changelog entry.
- [x] **Step 5: Commit.** Suggested summary: `Preserve numeric precision in table sorting`.

## Task 4 — Integration, review and delivery

**Files:** the changes above; update `docs/roadmap.md` with evidence only after merge.

- [x] Run the full committed worktree suite with the preparation command. Expected: no failures; the count will exceed the 389-test baseline.
- [x] Run relevant visual checks:

```sh
TEXTUI_VISUAL_TESTS=1 uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest tests/visual -q
```

Expected: reviewed baselines pass; a lifecycle/sorting fix should not require unrelated baseline updates.

- [x] Run packaging and lint checks:

```sh
uvx --python 3.12 --from pyflakes pyflakes textui
uvx --python 3.12 --from poetry==2.4.3 poetry check --lock
uvx --python 3.12 --from poetry==2.4.3 poetry build
git diff --check
```

Expected: no lint/diff errors, consistent metadata/lock and successful wheel/sdist build.

- [x] Obtain independent review of R1–R5 and the five Review Focus conditions. Fix important findings and rerun affected checks.
- [x] Open one reliability PR linking this spec/plan, the reproductions, behavior changes and validation evidence. Wait for Python 3.11/3.12/3.14, visual, lint and clean-wheel CI; inspect reviews/comments, fix verified feedback and resolve applicable threads.
- [x] Merge the verified PR, sync the root checkout without altering unrelated files, and record the merged PR/test results against Phase 0. Recheck late feedback before starting Phase 1.

## Self-review

Task 1 covers R1–R3 and close/supersession edge cases; Task 2 covers R4 and completion-registration races; Task 3 covers R5 and sort/refresh atomicity; Task 4 covers integration and review. Later roadmap phases require their own bounded designs and plans. This plan does not authorize changing dependencies or introducing new public runtime abstractions.
