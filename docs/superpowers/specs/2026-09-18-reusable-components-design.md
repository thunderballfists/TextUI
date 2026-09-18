# Reusable component design

## Goal

Let a `.ui` project define and reuse HTML-like components without embedded Python or expression evaluation. Components provide typed string properties, named content slots, fallback slot content, and instance-local internal IDs.

## Authoring format

An entry document imports a component explicitly:

```xml
<ui>
  <component src="components/agent-card.ui" as="agent-card" />
  <agent-card name="Alpha" status="Idle">
    <slot name="actions"><button on-pressed="open_alpha">Open</button></slot>
  </agent-card>
</ui>
```

The imported file has a `<component>` root with an optional property declaration and exactly one widget root:

```xml
<component>
  <props>
    <prop name="name" required="true" />
    <prop name="status" default="Unknown" />
  </props>
  <vertical class="agent-card">
    <label>{name}</label>
    <label>{status}</label>
    <slot name="actions"><button>Details</button></slot>
  </vertical>
</component>
```

`<component>` imports are allowed only directly below the entry `<ui>` root. The `as` name is lower kebab-case and applies only to that project document. A component source is local, UTF-8, and resolved relative to the importing entry file.

## Expansion

Project discovery expands component instances before the existing loader lowers widget markup. Every declared property is a string. Required properties must be supplied; undeclared properties are errors; defaults apply when omitted. `{property}` placeholders may appear in literal text and attribute values. They substitute only the declared property value and cannot access Python, evaluate expressions, or traverse object attributes.

Children supplied to a component instance must be `<slot name="…">` declarations. Each named slot replaces a matching placeholder in the component body. Omitted slots preserve their fallback children. Unknown slots and repeated named slots fail while loading. A component body may use one unnamed `<slot>` for ordinary child content; it also supports fallback children.

Imported components may instantiate other explicitly imported components. Imports and component expansion detect source cycles and report the source chain.

## IDs, events, and styles

The public `id`, class, style, and disabled attributes on a component instance apply to its rendered widget root. IDs declared inside a component are private to that instance and are rewritten with an instance prefix before normal document validation. Internal widgets are intentionally unavailable through `window.document.get_by_id`; controller code uses the component root's public ID or custom component APIs.

Events supplied in slot content remain normal document events. Component-template events are allowed only when their action name resolves through the importing project’s linked controller. Component TCSS remains entry-document styling in this first slice; component-local style files are deferred.

## Errors and validation

Discovery reports contextual `DocumentLoadError` or `DocumentValidationError` for unreadable sources, malformed component roots, invalid imports, invalid property declarations, missing required values, unknown properties, unknown or duplicate slots, malformed placeholders, duplicate public IDs, and import cycles. After expansion, the existing registry, structural validation, action validation, and style validation continue unchanged.

## Testing and documentation

Tests cover source resolution, imports, typed loader expansion, properties and defaults, named/default slot replacement, local-ID isolation across instances, event forwarding from supplied slots, invalid declarations, and import cycles. A runnable project example demonstrates a card component with caller-provided actions. The project-runtime guide, README markup table, migration guide, and changelog describe the new authoring contract.

## Deferred work

This version does not add Python props, reactive property updates, general expression syntax, dynamic repetition, conditional templates, component-local scripts, component-local styles, or a global component package registry.
