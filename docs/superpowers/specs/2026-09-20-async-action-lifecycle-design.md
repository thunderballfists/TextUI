# Async Action Lifecycle Design

## Purpose

TextUI actions need an opt-in lifecycle for data-backed controls. A declared action can expose loading, error, cancellation, and supersession without each application rebuilding task tracking and generation guards.

## Public API

`@action` and `@command` gain optional `target` and `supersede` arguments. `target` names a declared document ID. `supersede=True` cancels an earlier active invocation with the same action name and target. Existing declarations retain their current behavior.

The action receives the normal `ActionContext`. When lifecycle options are active, `context.target` returns the mounted target widget and `context.cancelled` reports whether the invocation has been superseded or shutdown has cancelled it.

## Runtime behavior

Before an awaitable action begins, TextUI adds a `-loading` class to its target and clears its prior lifecycle error. Completion removes `-loading`. A normal exception removes `-loading`, stores a readable error on the target, adds `-error`, and reaches the existing source-located error path. Cancellation removes `-loading` and does not become an error.

TextUI owns a task registry keyed by action name and target ID. A superseding call first cancels the previous task, then starts the replacement. Only the current task may update lifecycle state. Shutdown cancels all owned tasks and clears loading state.

## Boundaries

This version does not create a visual spinner, empty-state component, timeout option, retry policy, or automatic protection against application code that writes directly to an obsolete widget reference. It supplies target state and cancellation so controls and applications can choose their own presentation.

## Validation and tests

Document binding validates that every lifecycle target is a declared ID. Tests cover target lookup, loading/error class transitions, cancellation and stale completion suppression, shutdown cleanup, source context for errors, and unchanged legacy actions.
