# TextUI Documentation

These guides describe the current checkout. PyPI's latest published release is 0.7.0; registry inspection and generated authoring/static-check tools are unreleased on `main`. See the [changelog](../CHANGELOG.md) for release boundaries. To match an installed version, use documentation from its tagged source archive.

## Start here

1. [Install and run](../README.md#install-and-run): distribution name, isolated checkout setup and the `./showcase` launcher.
2. [Examples](../examples/README.md): choose a runnable project or integrate a document into a normal Textual App.
3. [Project runtime](project-runtime.md): linked Python/TCSS, includes, components/slots, lifecycle, commands, timers, panes and modals.

Use module commands with the interpreter where TextUI is installed. Checkout commands require the README's environment policy in the current shell; a global `textui` command or `.venv/bin/textui` is not assumed.

## Current reference

| Guide | Purpose |
| --- | --- |
| [Markup reference](markup-reference.md) | Generated built-in tags, typed attributes, defaults, native messages and grammar rules |
| [Controls](controls.md) | Control events, tables, trees and transcript selection |
| [Editor setup](editors.md) | Schema profiles, completion data, static diagnostics and validation limits |
| [Registry metadata](registry-metadata.md) | Explicit custom registrations and inspectable types/content constraints |
| [LLM reference](llm-reference.md) | Generated self-contained grammar, examples and common mistakes |
| [Migration](migration.md) | Distribution rename, unreleased additions and the historical interface reboot |

The generator owns `markup-reference.md`, `llm-reference.md`, root `llms.txt` and the four files in `spec/`. Do not hand-edit them; change registry metadata or `textui/authoring/` facts and regenerate. Static checks resolve declarative markup; trusted checks execute linked Python and construct widgets. Neither replaces mounted interaction tests.

## Contributors and maintainers

- [Testing](testing.md): headless interactions, artifact parity, opt-in visual baselines and fresh wheel verification.
- [Releases](releases.md): version preparation, trusted publishing and checks of the published artifacts.
- [Roadmap](roadmap.md): current priorities, completion gates and shipped work. This is the status authority.
- [Repository guidelines](../AGENTS.md): contributor workflow and repository constraints.

## Historical evidence

Dated [designs](superpowers/specs/) and [implementation plans](superpowers/plans/) record decisions for their original scopes. The [core design](superpowers/specs/2026-09-17-textui-core-design.md) describes the initial six-widget 0.2 reboot, not today's full catalog. Old exclusions and unchecked task lists do not override current guides, tests or roadmap status.

The [repository audit](audits/2026-09-17-repository-audit.md), [extension triage](2026-09-19-extension-triage.md), [reboot notes](../TEXTUI_REBOOT.md) and [original start prompt](../CODEX_START_PROMPT.md) retain their dated context. Library compatibility claims in the triage need rechecking before adoption. These records are preserved rather than rewritten as current setup instructions.
