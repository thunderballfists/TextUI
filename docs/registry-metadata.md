# Registry metadata

Registrations describe attribute domains, defaults, events and ordered content rules. Inspection does not run converters, factories, linked scripts or lifecycle hooks. This is the metadata foundation for [issue #96](https://github.com/thunderballfists/TextUI/issues/96). `textui spec` now generates built-in references, schemas and completion data from these descriptions; see [authoring tools and validation limits](editors.md).

## Inspect registrations

```python
import json
from textui.widgets.builtin_widgets import default_component_registry

registry = default_component_registry()
print(json.dumps(registry.describe(), indent=2))
print(registry.get("tabbed-content").describe())
```

`AttributeSpec.describe()` returns `type`, `required`, an optional `default`, and optional `doc`. `ComponentSpec.describe()` returns `tag`, `attributes`, `text_policy`, `content` and `events`. Event descriptions name the registered message class; forwarding remains the host's responsibility. `ComponentRegistry.describe()` also includes common attributes and named document-wide checks. Common attributes are shared declarations; data-only restrictions are recorded separately.

Descriptions are fresh dictionaries/lists, and defaults are copied with the existing default-copy policy. Built-in descriptions are JSON serializable. Custom defaults retain their Python values and may need an application-specific serializer. These descriptions are registry data, not an XSD or a complete standalone validator.

## Attribute types

Import types from `textui.metadata`. Each frozen type supports both `convert(value)` and callable conversion, plus `describe()`:

| Type | Domain |
| --- | --- |
| `Text()` | Literal string; preserves whitespace. |
| `Bool()` | Exactly `true` or `false`. |
| `Int(minimum=None, maximum=None)` | Base-10 integer with optional inclusive bounds. |
| `Enum(*values)` | One of the declared literal strings. |
| `Pattern(pattern)` | String matching Python `re.fullmatch`. |
| `IdRef(among="document")` | String reference with a described scope; contextual resolution remains a separate check. |
| `Number(positive=False)` | Finite nonnegative number, or strictly positive when requested. |
| `ValidatedText(name, converter)` | Named domain using an explicit validator. |

`integer(minimum=...)` and `enum(...)` retain their callable API and return described types. `AttributeSpec(str)` and `AttributeSpec(boolean)` are recognized automatically. Other existing callables still work and are described as `custom`; inspection never probes them. Supply `value_type=` to describe a legacy converter without replacing it. The actual `converter` remains authoritative, so its declared metadata must agree with it.

Built-in named domains preserve existing validators: Unicode alphanumeric tab accelerators, Python command identifiers, nonempty data keys and direct-mapping runtime-list formats. An accelerator is not limited to ASCII. `IdRef` adds no lexical restrictions or automatic reference resolution.

## Declare content

Import constraints from `textui.content`. Set `child_policy="widgets"` and matching `Children(policy="widgets")` explicitly; existing registrations without `content` remain supported.

```python
from textual.containers import Vertical
from textui import ComponentSpec
from textui.content import Children, Count, ElementRef, Only

registry.register(ComponentSpec(
    "label-stack", lambda context: Vertical(*context.children),
    child_policy="widgets",
    content=Children((
        Count(minimum=1, message="label-stack requires a label"),
        Only((ElementRef("label"),), message="label-stack accepts only labels"),
    )),
))
```

Rules run in declaration order, before descending into children. Failures retain the node's source location and the declared diagnostic. `ElementRef(tag)` matches spelling; `ElementRef(tag, factory)` matches factory identity, preserving native aliases.

Available document constraints are `Parent`, `RequireCommon`, `Needs`, `Only`, `Count`, `Sequence`, `UniqueSlots` and `ForbidCommon`. `NamedCheck(name, doc, check)` describes explicit compound code. Its callback receives `(node, parent)`; inspection never calls it. Non-document phases describe checks owned by other validation stages.

`ForbidCommon` describes value-sensitive predicates: present `id`/`style`, nonempty normalized class tokens and `disabled=true`. Native data children also reject declared events. The earlier tag-based lowering check rejects any common attribute on canonical data-only tags, including `disabled=false` or `autofocus`; unrelated custom factories with those tag names can still declare events.

`NativeChildren(widget_type, message, minimum=0, maximum=None)` describes construction-time instance checks. Builders call `validate_build(context.children)` when native children exist; it accepts subclasses. Declaring this rule does not move it into loading or automatically call it from custom builders.

## Migrated and explicit rules

| Rule family | Ownership |
| --- | --- |
| Modal root/ID; option, tab-pane, slot and data-child parents | Declarative document constraints. |
| Select, tabs and radio child types/minimum counts | Declarative document constraints. |
| Tab accelerator/scope dependencies | Ordered `Needs` constraints. |
| Bar slot types/uniqueness; row/tree child types | Declarative document constraints. |
| Table column/row types and column-before-row order | `Only` and `Sequence`. |
| Split's two Pane children; navigation's NavItem children | Shared `NativeChildren` metadata, enforced during construction. |
| Select values, initial tabs, radio events/selection, progress/range bounds | Named explicit compound checks. |
| Table column requirements, keys/row widths; tree keys | Named explicit compound checks. |
| Duplicate IDs, common identifiers/data-only attributes, navigation references, accelerators, TCSS | Named document rules; original validation stages retained. |
| Bar native slot instances/positions, seed-builder defensive checks | Explicit construction checks; bar check described by name. |

Built-in declarations are centralized in `textui/widgets/metadata.py`. Legacy registrations reusing a native factory inherit its existing structural rules when no explicit content is supplied. Unrelated factories using built-in tag names retain their existing behavior. Some lowering/reference checks are historically tag-based; their named descriptions record that boundary.

Developer-authored registrations and documents remain trusted. Ordinary `textui check` still executes trusted linked scripts. The separate `textui check --static` mode uses the built-in registry plus declarative components and includes; it cannot infer Python registrations without execution. Neither mode is a sandbox.
