# Authoring and Editor Setup

These authoring additions are unreleased on `main`; use the current checkout until the next PyPI release. Installed-wheel support is covered by packaging tests.

Generate the reference tree from a checkout or installed wheel:

```sh
python -m textui spec --output ./textui-authoring
python -m textui check --static --format json /path/to/app.ui
```

In this repository, run through `uvx --python 3.12 --from poetry==2.4.3 poetry run python -m textui`; regenerate committed copies with `spec --output .`. Generation replaces its seven artifact files. Other files are untouched. It reads registry metadata and bundled examples, without constructing widgets or invoking converters. Tests fail if committed artifacts or bundled examples drift.

## Choose a schema profile

| File | Use | Limits |
| --- | --- | --- |
| `spec/textui.xsd` | Built-in markup without includes, or expanded structure; precise child completions | Rejects unexpanded includes in every position, component imports/aliases and template placeholders. |
| `spec/textui-authoring.xsd` | Raw projects using reusable components, includes and templates | Skips widget bodies and templates, so aliases that shadow built-ins work; unknown tags, attributes, values and misplaced children can pass. Static checking is required. |

Both profiles use no target namespace. The strict schema describes exact booleans/enums, required attributes, simple child choices/counts/sequences, data-only attributes and bar slots. IDs/references stay strings rather than `xs:NCName`; native Textual identifiers have their own rules. Integer lexical syntax is checked, while numeric bounds, finite numbers, dependent attributes, duplicate IDs, references, compound rules, TCSS and parser restrictions require TextUI. Global element declarations can also validate standalone elements; TextUI enforces the document's `<ui>` root. The executable [exception list](../tests/fixtures/schema_exceptions.json) records structural rules that the XSD cannot fully express; these remain authoritative static checks.

An alias such as `<component src="card.ui" as="input" />` can render a label or container instead of the built-in input. Applying a built-in schema type to it would report false errors. The permissive profile therefore skips body validation entirely; its global declarations retain authoring metadata, but static expansion determines the actual types and validates their properties. Use the strict profile when precise child/value completion and schema validation are needed for built-in-only markup.

Includes may supply several children, such as both panes of a split. The strict profile applies child models to the expanded structure and intentionally rejects raw `<include>` directives, including at the root. Select the permissive profile for raw include-based projects and run static checking; do not apply the strict profile directly to those files. Tests cover root and nested includes, constrained containers and the resulting expanded strict grammar.

Use the [generated markup reference](markup-reference.md) for types, defaults, events, grammar and validation phases, or the self-contained [LLM reference](llm-reference.md) when generating markup.

## VS Code XML

Install Red Hat's XML extension. `.ui` also belongs to Qt Designer in some editors, so place associations in this project's `.vscode/settings.json`, not global settings. For built-in-only files:

```json
{
  "files.associations": { "*.ui": "xml" },
  "xml.fileAssociations": [
    { "pattern": "**/*.ui", "systemId": "${workspaceFolder}/spec/textui.xsd" }
  ]
}
```

Point `systemId` to `spec/textui-authoring.xsd` instead for projects using reusable components or includes. If you generated into another directory, adjust the path. Workspace schema mappings provide completion and validation without modifying markup; see the extension's [file association documentation](https://github.com/redhat-developer/vscode-xml/blob/main/docs/Validation.md#xml-file-association-with-xsd).

Do not add `xmlns:xsi`, `xsi:noNamespaceSchemaLocation` or an `<?xml-model ...?>` instruction. The loader rejects namespaces, root attributes and processing instructions; regression tests confirm that `xml-model` is rejected.

## HTML completion data

VS Code's HTML language service can load the generated tags, attributes and literal values:

```json
{
  "html.customData": ["./spec/vscode-html-custom-data.json"]
}
```

This setting applies in HTML mode, not Red Hat XML mode. Use it only as an optional completion/hover aid; HTML parsing and formatting cannot validate TextUI's grammar or preserve all self-closing controls. Keep strict XML syntax and run static checks. See [VS Code custom data](https://code.visualstudio.com/api/extension-guides/custom-data-extension).

## JetBrains and other XML editors

Use project file-type settings to recognize `.ui` as XML rather than Qt UI. Map the local no-namespace schema in **Settings → Languages & Frameworks → Schemas and DTDs**, choosing the strict or authoring profile above. A generated schema location is an editor mapping, never an attribute on `<ui>`. See [JetBrains schema mapping](https://www.jetbrains.com/help/idea/referencing-xml-schemas-and-dtds.html).

`spec/web-types.json` provides HTML completion/hover contributions in tools that load [JetBrains web-types](https://github.com/JetBrains/web-types). It is not an XML schema, and generating it alone does not automatically enable an IDE provider. Use the schema mapping for XML editing; provider configuration depends on the IDE. Oxygen and other XML editors can likewise associate a local no-namespace schema externally.

## Static and trusted checks

`check --static` expands declarative components/includes, validates built-in literals and document rules, and infers known split/nav child constraints. It never imports linked controllers, runs hooks or constructs an App/widget. Linked files must exist. Controller-registered tags cannot be inferred without executing code; use trusted `check` for such extensions.

`--format json` is available only with static mode. It emits an array of records with `file`, `line`, `column`, `element`, `attribute`, `message`. Success emits `[]`; validation is fail-fast and expected failures emit one record. Unavailable location fields are null. Expected JSON diagnostics are on stdout; unexpected failures retain a traceback on stderr. Exit codes: 0 success, 1 project error, 2 usage error, 3 unexpected failure, 130 interruption.

Static checking does not validate callable actions/commands, native constructor behavior, TCSS, theme variables or mounted layout. Existing `check` runs linked Python and setup/close hooks, binds actions and builds widgets; a running-app test still covers mounting and interactions. Documents and registrations remain trusted inputs; this is not a sandbox.

## Maintainer verification

Automated tests compile both schemas, compare generated artifacts, cover all example files and schema/loader agreement, and exercise generation/static checks in a fresh wheel-only environment. Completion JSON has also been checked against the upstream format schemas.

Before declaring IDE integration verified, manually open `examples/controls/app.ui` in VS Code with the strict schema, request children of `tabbed-content`, and confirm `tab-pane` completion and the `document` value for `accelerator-scope`. Repeat with the permissive profile for a component project and run static validation. Extension UI completion has not been claimed as an automated test.
