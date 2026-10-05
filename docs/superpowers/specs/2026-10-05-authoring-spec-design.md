# Generated authoring specification and static checking

Issue #96, PR 3; base `a2d59f8`. Implement without changing accepted runtime markup, dependencies, version, distribution, import, or console-script names.

## Static boundary

`textui check --static PATH` discovers includes and component declarations, expands reusable components, and lowers against the built-in registry. It runs existing declarative and named document checks. Canonical built-in split/nav child types and counts are also checked from metadata without constructing widgets. It does not import controllers, construct an App or Widget, bind actions, parse native TCSS, or invoke lifecycle hooks. Files remain trusted project inputs; this is not a sandbox. Controller-defined registrations, actions/commands, native constructor constraints, styles and mounted behavior require the existing trusted `textui check`.

`--format json` is available with `check --static` only. Stdout is an array of diagnostic records with exactly `file`, `line`, `column`, `element`, `attribute`, `message`; successful checks emit `[]`. Checking remains fail-fast, so expected failures contain one record. Existing error locations and exit codes are retained. Unexpected errors still use stderr and exit 3. Text mode retains contextual errors and a success line.

## Generator and packaged inputs

`textui spec --output DIRECTORY` (default current directory) generates stable UTF-8, newline-terminated artifacts from fresh built-in registry descriptions. No widget factories or attribute converters are invoked. Shared authoring facts cover project directives, component format, canonical examples and common mistakes. Examples are bundled with the Python package so generation works outside a checkout; tests compare their content to the repository originals.

Generate `docs/markup-reference.md`, `spec/textui.xsd`, `spec/textui-authoring.xsd`, `spec/vscode-html-custom-data.json`, `spec/web-types.json`, `llms.txt`, and `docs/llm-reference.md`. Include `spec/` and `llms.txt` in source distributions. Editor JSON is completion data, not an HTML parser or full validator. References enumerate every registered element, common and specific attributes, defaults, required flags, events, content rules, named checks and component syntax.

## Schema scope

The strict no-namespace XSD describes built-in vocabulary, exact boolean/enum literals, required attributes, simple containment/count/sequence rules and data-only attribute restrictions. XML Schema cannot fully capture contextual references, Python Unicode identifier and number domains, native TCSS, or arbitrary reusable-component aliases. Such cases have explicit test allowlists and prose limits. Do not use `xs:NCName` for references: it would narrow the runtime's string/reference domain.

The additional authoring profile permits dynamic component aliases and placeholders, and validates known built-ins where possible. It deliberately cannot reject unknown aliases and skips component template bodies. Raw examples use that profile; their expanded built-in documents also validate against the strict schema. Static checking is authoritative for aliases and compound rules. Processing instructions remain rejected; editor schema association is workspace configuration.

## Delivery gates

Pin generation drift, loader/schema structural agreement with explicit exceptions, all project examples and complete README/LLM examples, and each stated common mistake. Prove nonexecution with a controller that would write a marker and raise, with includes/components and widget/App constructor sentinels. Extend fresh installed-wheel smoke to generate all artifacts and check a component project statically. Run full headless tests, visual regression checks, Pyflakes, lock/build and wheel-only verification; review the branch and all PR feedback before integration. Mark roadmap 1C delivered; manual editor extension completion verification remains a stated maintainer check, not an automated claim. No release publishing.
