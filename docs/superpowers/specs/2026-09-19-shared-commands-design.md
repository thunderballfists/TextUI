# Shared Commands Design

## Goal

Give project scripts one declaration for an operation that may be invoked from a markup control or a keyboard shortcut. The first release covers command buttons and shortcuts; menus, palettes, and dynamic availability can reuse the same metadata later.

## Public contract

Linked scripts declare a command with a zero-argument function. `window` remains the application facade, so command bodies need no application plumbing.

```python
from textui import command

@command(label="Quit", shortcut="ctrl+q", description="Exit the application")
def quit_app():
    window.app.exit()
```

Use it in project markup without duplicating the label or event directive:

```xml
<command-button id="quit" command="quit_app" variant="error" />
```

`label` defaults to a title-cased function name (`open_help` becomes `Open Help`). `shortcut` is optional. Its description is shown by Textual's binding help; it defaults to the label. `enabled` is an optional boolean and defaults to `true`. Disabled commands render disabled command buttons and ignore their shortcut.

`@command` also exposes the function as an ordinary action under its Python name, preserving an escape hatch for existing `on-*` directives. Commands accept no parameters so pointer and keyboard invocation always run the same callback; event-aware behavior remains an `@action`.

## Runtime model

`ControllerSet` validates each decorated command while loading linked scripts, creates immutable metadata, and supplies an action wrapper for ordinary document dispatch. A bound document receives the command mapping, validates every `<command-button>` reference before composition, resolves its label and disabled state, and routes its `Button.Pressed` message through the existing action dispatcher.

`ProjectApp` installs declared shortcuts after binding the document. Its `textui_invoke_command` action calls the document command dispatcher, which applies the enabled guard and awaits the exact controller callback. This keeps errors contextual and avoids a second callback path.

The direct `TextUI(document, actions=...)` convenience host intentionally remains action-only in this release: commands depend on linked controller declarations. Native hosts can continue to forward ordinary markup actions themselves.

## Validation and compatibility

Command names are Python identifiers from function names and must be unique across linked scripts. Command functions must take zero positional parameters. Labels, descriptions, and shortcuts must be non-empty strings when supplied, and `enabled` must be a boolean. A command button must name a declared command; failure is a source-located document validation error on its `command` attribute.

Existing `@action`, `on-*` directives, ordinary `<button>`, and tab accelerators retain their behavior. No dependencies are added.

## Deferred work

Dynamic enabled predicates, explicit command refreshes, menus, a command palette, and user-configurable key maps are separate follow-up work. Static availability makes the first control and shortcut contract testable without inventing reactive state APIs.
