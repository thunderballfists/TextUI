# Initial Codex Prompt

Paste the text below into the first Codex thread opened on this repository.

---

We are considering a deliberate reboot of TextUI, an experimental declarative
markup layer over Textual. Read `AGENTS.md` and `TEXTUI_REBOOT.md`, then inspect
the repository, tests, dependency configuration, and git history.

For this first task, do not change application code, dependencies, or public
APIs. Treat the reboot brief as design context rather than an unquestionable
specification: verify its claims and challenge its proposed direction where the
current repository or current Textual APIs provide better evidence.

Investigate the project in two environments:

1. reproduce the current baseline using the repository's declared dependency
   constraints;
2. test against the current stable Textual release in an isolated environment
   without committing dependency changes.

Use current official Textual documentation, API references, and release notes
when analyzing compatibility. Verify the current stable version rather than
assuming the version recorded in the brief is still current.

Return a repository audit that covers:

- current architecture and actual behavior, including how the document root,
  nested widgets, styles, generated IDs, scripts, and DOM-like helpers work;
- baseline test results and exact relevant versions;
- failures or behavioral changes on current Textual, grouped by root cause;
- gaps in the existing tests and mismatches between the README and code;
- which concepts/code should be retained, adapted, or removed;
- whether TextUI should subclass `App`, wrap an existing `App`, or separate a
  document loader from an optional app convenience;
- two or three architecture options for a typed component registry,
  declarative registered actions, useful validation errors, and custom
  components;
- parser and dependency choices, including whether `lxml`, the custom CSS
  validator, and mandatory image support are justified;
- a recommended minimal architecture and the smallest widget set needed to
  prove it;
- unresolved product/design choices that need my decision;
- a staged, testable implementation plan, but no implementation yet.

Keep the project narrowly framed as a declarative authoring layer for Textual:
markup for structure, TCSS for appearance, Python for behavior, and Textual for
the runtime. Do not propose a new renderer, JavaScript runtime, general template
language, or large reactive framework unless repository evidence makes one
unavoidable.

Important safety/design boundary: arbitrary embedded Python via `<script>`
should not remain the default event mechanism. Evaluate a registry of
application-exposed actions such as `on-pressed="save_document"`. Do not claim
that markup is safe for untrusted or model-generated content without defining a
real threat model and enforceable allowlists.

End with a short decision checklist for me. Stop after presenting the audit and
recommendation; wait for approval before writing a design spec or changing
code.

---
