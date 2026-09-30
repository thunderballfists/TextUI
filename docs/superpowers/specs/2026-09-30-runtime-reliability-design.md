# Runtime Reliability Design

Date: 2026-09-30. Status: proposed for implementation. Baseline: `f8e472c`.

## Purpose and scope

Implement Phase 0 of the [roadmap](../../roadmap.md): fix five defects confirmed by headless review probes. Consolidate only the duplicated lifecycle logic needed to fix them. Keep markup, action/command decorators and native host integration compatible.

| Finding | Evidence at baseline | Owner |
| --- | --- | --- |
| R1: async work survives shutdown | An untargeted action remained pending after ProjectApp closed, then resumed with `window.phase == "closed"`. `document.py:424` cancels only lifecycle-target tasks. | 0A |
| R2: synchronous target state is never completed | `@action(target="status") def refresh(): pass` returned with `-loading` still set. Synchronous exceptions also bypass target error cleanup. See `document.py:552`. | 0A |
| R3: shared-target loading is cleared early | Two different actions targeting `status` ran concurrently; completing the first removed loading with the second still pending. See `document.py:579`. | 0A |
| R4: completed timer workers are retained | Fifteen async ticks retained fifteen finished workers; threaded ticks use the same retained collection. See `timers.py:76,92`. | 0B |
| R5: numeric sorting loses precision | Ascending rows containing `2**53 + 1`, then `2**53`, remained in that order because both keys became the same float. See `data_widgets.py:359`. | 0C |

## Constraints

- Python `>=3.11,<4`; Textual `>=8.2.8,<9`; lxml `>=6.1.3,<7`.
- Poetry 2.4.3; no added product dependencies or hand-edited lock resolutions.
- Strict XML, linked trusted Python, native TCSS and explicit custom-message forwarding remain unchanged.
- Core must not import or install Pillow or textual-imageview.
- Tests use headless Textual/Pilot and strict function-scoped asyncio loops; screenshots remain opt-in.
- Preserve exact registered message-type/source identity dispatch, immediate-error propagation, delayed-error reporting with source/cause, and native bubbling.
- Cancellation is cooperative. This work cannot force-stop a thread or prevent side effects from application code that deliberately suppresses cancellation.

## 0A — Invocation ownership

Extract a private `InvocationOwner` in `textui/invocations.py`. BoundDocument remains responsible for event matching, callback arguments, public errors and delivery to Textual's native error path. The owner handles invocation records, target state, supersession and asynchronous task ownership for both event actions and commands.

Each private `OwnedInvocation` records its name, optional target, existing `ActionInvocation` context state, optional task and generation. Keep action-specific supersession keyed by `(name, target)`, while loading ownership and latest-generation state are tracked per target widget.

Start lifecycle state before executing either a synchronous or asynchronous callback. A new target invocation clears its previous error. Register the replacement before cancelling older invocations so their cleanup cannot briefly clear replacement loading. `supersede=True` cancels only prior invocations with the same name and target; another action sharing that target continues.

Every invocation finishes exactly once, including synchronous success/failure and cancellation. A target keeps `-loading` until all its active invocations finish. Only the newest started generation may publish target error state; an older completion must not overwrite a newer result. Cancellation does not add `-error`. Source-located action/command errors retain their existing reporting behavior; suppressing stale target state does not silently swallow an ordinary callback failure.

Track all callback awaitables, including those without a target. Also track shortcut wrapper tasks created by `start_command`. On close, mark ownership closed first, mark cancelled contexts, request cancellation for every owned task, clear loading/ownership and tolerate later completion callbacks. Do not block synchronous `close()` waiting for arbitrary user code.

Both convenience Apps close their document when exit begins and on unmount; repeated close is harmless. Normal Textual hosts call `bound_document.close()` during shutdown, documented explicitly. Closing `dispatch(message)` ignores queued messages by returning `False`; direct `invoke_command(name)` raises `DocumentStateError`; `start_command(name)` becomes a no-op. These guards run before callbacks or tasks are created. Disabled-command behavior while open remains unchanged.

Public signatures remain `dispatch(message) -> bool`, `invoke_command(name) -> bool`, `start_command(name) -> None` and synchronous `close() -> None`. Existing ActionContext properties remain supported; invocation cancellation state is available for untargeted actions as well.

## 0B — Timer ownership

Keep only active Workers in `RuntimeTimers.workers`. Consume native `Worker.StateChanged` messages in ProjectApp and forward them to its timer owner; do not add automatic markup-event discovery. Remove owned workers on SUCCESS, ERROR or CANCELLED, without suppressing Textual's error handling.

Registration must handle a worker completing immediately, including a fast thread: add it, then check its current terminal state. Close stops handles, requests worker cancellation, and clears both ownership collections. Late state messages are harmless. Repeating ticks still skip overlap; finished worker cleanup must not change when callbacks execute or their source-located errors are reported.

## 0C — Exact numeric sorting

Compare `numbers.Real` values directly rather than coercing to float. Preserve the existing ascending category order: booleans, numeric values, then case-folded textual values; descending reverses that order. Equal keys remain stable. Decimal and other non-Real objects retain their current textual treatment; adding typed column comparators is separate work.

Missing required record fields remain validation errors. `None` retains textual `"None"` ordering. Numeric NaN uses textual `"nan"` ordering, avoiding unordered numeric comparisons; positive and negative infinity remain numeric. Document these policies and test both sort directions. No automatic numeric parsing of seeded string cells is introduced.

Sort construction must complete before rows, cursor or active-sort metadata are mutated. Failed replacement validation preserves the previous table. Preserve the active column/direction on refresh and selected row identity when a declared row key survives.

## Acceptance

- Each R1–R5 reproduction fails before its fix and passes afterward.
- Sync/async actions and commands, buttons/shortcuts, shared targets, supersession, immediate/delayed failure and shutdown use consistent ownership rules.
- Cooperative tasks awaiting an Event are cancelled on exit, cannot later resume from that Event, and do not report cancellation as an error.
- Async and threaded timer runs release completed Workers; overlap skipping and shutdown regressions stay green.
- Adjacent integers above `2**53`, integers beyond float range, mixed types, NaN, infinities, stable ties and refreshed sorted tables behave as specified.
- Full committed suite, relevant visual checks, Pyflakes, lock validation, build and CI pass; docs/changelog are updated and review findings addressed.

The launch/validation tooling, compatibility matrix and new widgets have separate roadmap phases and are not included in this implementation.
