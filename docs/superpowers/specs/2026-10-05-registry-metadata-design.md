# Inspectable registry metadata

Implements the second deliverable of issue #96. The purpose is to give later documentation, schema and editor generators a dependable description of the existing markup contract. This change does not add those generators or static checking.

## Compatibility contract

Accepted markup, converted values, defaults, diagnostic text, source locations and validation order remain unchanged. Custom callable converters and registrations remain supported. Built-in matching uses factory identity where it does today; a custom tag with a built-in spelling is not automatically subject to that built-in's rules. Checks currently deferred to construction remain deferred. Python >=3.11, the existing lockfile, import/CLI names, and the image-free dependency boundary remain unchanged.

## Attribute descriptions

`textui.metadata` supplies frozen callable types with `convert(str)` and `describe()`: `Text`, `Bool`, `Int(minimum, maximum)`, `Enum(*values)`, `Pattern`, `IdRef(among)`, and `Number(positive)`. Calling a type delegates to conversion. Integer/enum convenience functions retain their callable interface and return the corresponding described type. Plain callable `AttributeSpec` converters retain their original runtime invocation.

`AttributeSpec.describe()` reports type information, required/default state and optional documentation. A callable without declared metadata is described as `custom`; describing it never executes the converter. Built-in specialized string validators get explicit named descriptions and retain their original validator, including Unicode alphanumeric accelerators, Python identifiers, nonempty keys and direct-mapping format patterns. `IdRef` describes the existing reference relationship without introducing lexical restrictions.

Descriptions return fresh structures; mutating one cannot change a converter, registration or subsequent description. Built-in descriptions are JSON serializable. Arbitrary custom defaults retain their existing Python values; no serialization guarantee is made for them.

## Content and rules

`ComponentSpec.content` describes the existing child policy and ordered constraints. Immutable constraints express parent/root placement, required common fields, dependent attributes, allowed children, child counts, sequence order, unique slots and forbidden common attributes/events. Element references record canonical names and preserve existing factory-, tag- or widget-type matching. Each constraint includes the existing diagnostic and validation phase.

A generic checker interprets simple constraints. Named explicit checks retain compound logic: select values, tab initial references, radio selection/events, progress/range relationships, table seed keys/row widths and tree keys. Their metadata includes a name and short description. Document-wide navigation references, duplicate IDs and accelerators retain their current stages and get named descriptions.

Built-in declarations live together in `textui/widgets/metadata.py`, enriching the explicitly registered immutable specs. The same factory-based declarations provide compatibility for older custom registrations that reuse a native factory without declaring content metadata. Custom registrations with unrelated factories use their own declared content or their existing permissive policy. Split and navigation builders share NativeChildren instance/count constraints with their descriptions; these stay construction-time checks and accept native subclasses. Bar/seed builders retain explicit defensive construction checks.

## Verification

Before refactoring, record representative invalid documents and their exact existing diagnostics. Include each migrated containment rule, combined-invalid cases that expose error precedence, Unicode accelerators, legacy converters and custom factories reusing tag names. Keep all existing tests unchanged. Verify every built-in attribute is described and each component has content metadata. Test custom metadata through real loading, and description isolation through repeated inspection.

Run the full headless suite, existing macOS/Linux visual comparison, lint, lock/build checks and wheel-only integration. Extend installed-wheel smoke with metadata inspection. Obtain independent review, inspect PR feedback and resolve verified findings before merge. Leave issue #96 open for its third deliverable.
