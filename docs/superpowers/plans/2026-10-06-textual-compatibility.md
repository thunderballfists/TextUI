# Textual Compatibility Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, with a fresh whole-branch review before integration.

**Goal:** Deliver roadmap Phase 2A: installed-wheel behavioral probes for the lowest and latest allowed Textual versions and a map of Textual internal touchpoints.

**Architecture:** Reuse existing regression tests through a standalone compatibility runner. Two fresh CI environments resolve the floor and newest permitted Textual independently of the Poetry lock, verify installed imports, then run focused probes and the complete wheel smoke.

**Tech Stack:** Python 3.12, pytest/Pilot, Poetry 2.4.3 builds, pip wheel resolution, GitHub Actions.

**Spec:** [Roadmap Phase 2](../../roadmap.md#phase-2--compatibility-and-maintenance), scoped to the first compatibility bullet and internal-touchpoint gate. The bounded design was presented in chat under standing autonomous-work authorization.

## Global Constraints

- Preserve Python >=3.11,<4, Textual >=8.2.8,<9, lxml >=6.1.3,<7 and the unchanged Poetry lock.
- No runtime/API/dependency/version changes, release or AGENTS.md edits.
- Existing locked Python 3.11/3.12/3.14, lint and visual checks remain intact.
- Compatibility tests import the installed wheel, not source; use -I, importlib pytest mode and a working directory outside the checkout.
- Reuse meaningful existing interaction/computed-style regressions; do not create tests that mirror workflow text.

## Review Focus

- Lowest/latest policies must be separate even when both currently resolve to 8.2.8.
- A passing source-checkout run must not be reported as an installed-wheel result.
- Selected test names must fail collection when stale, never silently shrink coverage.
- Constraint and floor checks must reject a future dependency-range mismatch instead of testing the wrong version.
- Platform/real-terminal/IDE behavior remains unverified by these Linux/headless probes.

### Task 1: Add installed compatibility checks and guidance

**Files:** Create `tests/compatibility_smoke.py` and `docs/compatibility.md`; modify `.github/workflows/tests.yml`, `docs/testing.md`, `docs/README.md`, `docs/roadmap.md`.

**Interfaces:** Reuse existing tests for stylesheet cascade/presets, gradient geometry, table rendering/sorting/resizing, log selection/streaming, splits, project resize hooks, modal reopen/private tabs, shutdown and custom host forwarding. Produce a standalone `python -I tests/compatibility_smoke.py {lowest,latest}` command plus two CI jobs.

- [x] Implement the test-only runner with installed-package origin and metadata checks, optional floor enforcement, explicit probe nodes and preserved pytest exit status.
- [x] Run against the editable checkout and confirm intentional rejection; then build and install a wheel in two separate temporary Python 3.12 environments with `textual==8.2.8` and the wheel's default latest allowed resolution. Expected: origin rejection for source; both installed policies pass their complete selected suite and `wheel_smoke.py`.
- [x] Add two CI matrix jobs using fresh environments and unlocked resolution, without modifying the locked jobs or lockfile. Log resolved versions and run pip consistency checks.
- [x] Document reproducible commands, floor/latest scope, internal touchpoints with matching regression tests, and remaining Phase 2 work. Verify links, lock/build, lint, the full 669-test suite and unchanged visuals.
- [x] Commit with an imperative summary and record verification.

## Integration

Fresh independent review, GitHub feedback and all seven CI jobs are required before merge. Resolve verified feedback, verify the merged main tree and post-merge CI. Do not claim Phase 2 as a whole complete; platform CI, forwarding consolidation and incremental typing remain pending.
