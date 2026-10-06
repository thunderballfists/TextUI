"""Non-registry project grammar and packaged canonical examples."""
from importlib.resources import files

from ..presets import STYLE_PRESETS


EXAMPLES = {
    path: files(__package__).joinpath("samples", path).read_text(encoding="utf-8")
    for path in (
        "examples/sample_markup.xml", "examples/form.xml",
        "examples/components/agent-card.ui", "examples/components/app.ui",
    )
}


def _text_attribute(*, required: bool = False) -> dict:
    return {"type": {"type": "string"}, "required": required}


# Project directives are parser grammar, not widget registrations. Keep their
# completion descriptions together with the grammar rather than fake factories.
DIRECTIVES = (
    {"tag": "ui", "doc": "Attribute-free project/document root.", "attributes": {}},
    {"tag": "style", "doc": "Entry-root embedded TCSS, or src/preset (mutually exclusive).", "attributes": {
        "src": _text_attribute(), "preset": {"type": {"type": "enum", "values": list(STYLE_PRESETS)}, "required": False}}},
    {"tag": "script", "doc": "Entry-root linked trusted Python controller; never embedded Python.", "attributes": {"src": _text_attribute(required=True)}},
    {"tag": "include", "doc": "Expand a local attribute-free ui fragment.", "attributes": {"src": _text_attribute(required=True)}},
    {"tag": "component", "doc": "Entry-root import (src/as), or attribute-free component-file root.", "attributes": {"src": _text_attribute(), "as": _text_attribute()}},
    {"tag": "props", "doc": "Component property declarations, before its widget root.", "attributes": {}},
    {"tag": "prop", "doc": "Empty component property declaration; required=true excludes default.", "attributes": {
        "name": _text_attribute(required=True), "default": _text_attribute(),
        "required": {"type": {"type": "boolean", "values": ["true", "false"]}, "required": False, "default": False}}},
    {"tag": "slot", "doc": "Named/default template slot with optional fallback, or named instance content.", "attributes": {"name": _text_attribute()}},
)

GRAMMAR = """Use one attribute-free `<ui>` root. Write well-formed UTF-8 markup with quoted attributes,
closed/self-closed lowercase kebab-case tags, and boolean literals `true` or `false`.
Comments, CDATA, the five predefined named entities and numeric character references work.
DTDs, namespaces, processing instructions, unknown tags/attributes/events and duplicate IDs are rejected.
Text is literal; text-area preserves whitespace. Other text leaves collapse whitespace.
Containers cannot mix non-whitespace text and child widgets; leaf controls cannot contain markup.
This vocabulary is not HTML: `<switch />` is a valid TextUI element, bare attributes and `&nbsp;` are invalid.
Events use `on-` plus the registered event name; values are Python action identifiers, never expressions.

At the entry root, `<script src="controller.py" />` links trusted Python and
`<component src="card.ui" as="card" />` declares a reusable component alias.
`<include src="views/body.ui" />` expands a local attribute-free `<ui>` fragment (also inside containers).
`<style src="app.tcss" />`, `<style preset="compact" />`, or embedded `<style>` supply TCSS.
Script/style/component declarations belong only at the entry root; URLs and include/import cycles are rejected.

A component file has one attribute-free `<component>` root, optional component imports,
optional `<props>` with empty `<prop name="title" required="true" />` or
`<prop name="status" default="Ready" />` declarations, and exactly one widget root.
Property names and aliases are lowercase kebab-case. Required properties cannot have defaults.
Template `{property}` substitution is single-pass. Template IDs are private and prefixed per instance.
`<slot />` is the default slot; `<slot name="actions">fallback widgets</slot>` declares a named slot.
Instances supply children to the default slot or wrap named content in `<slot name="actions">...</slot>`.
Pass runtime-list record formats through a property: `row-format="{name}"` on an instance and
`item-label="{row-format}"` in its template. `{{name}}` does not escape component substitution.
"""

LIMITS = """`textui check --static PATH` resolves includes and declarative components against built-ins,
checks literal attributes, IDs, references, simple containment and named document rules,
and checks canonical split/nav child types without constructing widgets.
It never imports linked controllers, invokes lifecycle hooks, binds actions or constructs Apps/widgets.
`--format json` emits an array of `{file, line, column, element, attribute, message}` records;
success is `[]`, and expected failures contain the first error. Exit codes: 0 success, 1 project error,
2 CLI usage, 3 unexpected error, 130 interruption. Missing line/column/element/attribute values are null.

This does not validate controller-defined registrations, callable action/command exposure,
native constructor constraints, TCSS or mounted behavior. Run the existing trusted `textui check PATH`
for those checks; it executes linked Python, setup and close hooks. Neither mode is a sandbox.

`spec/textui.xsd` is the strict built-in grammar without includes, or after declarative expansion:
no target namespace, exact booleans/enums,
required attributes and simple content models. References remain strings, not `xs:NCName`,
so the schema does not narrow native Textual ID semantics. Integer lexical syntax is checked;
bounds, finite numbers, Unicode/native identifiers, compound checks and TCSS require static/runtime checks.
Duplicate IDs, reference resolution, dependent attributes and named compound rules are not fully
expressible in this XSD. Parser restrictions such as DTD/PI rejection also require TextUI's parser.
Global element declarations also accept standalone elements; TextUI's parser enforces the ui document root.

`spec/textui-authoring.xsd` permits aliases, includes and template placeholders. Aliases can shadow built-in
names, so this profile deliberately skips all ui widget bodies and component templates, including literal
attribute checks. A schema pass is not project validation; run static checking for those rules.
Use it for raw component/include projects; use the strict schema for built-in markup without includes
or for the expanded built-in structure. Includes can supply multiple children; no unexpanded include
position is checked by the strict profile. The checker resolves them before validating child models.
HTML custom data and web-types provide completions/hover only. Keep the XML parser and use workspace
associations: `.ui` is also used by Qt Designer. Do not add an `xml-model` processing instruction.
"""

MISTAKES = (
    ("Uppercase tags", '<ui><Button/></ui>', "element name must be lowercase kebab-case"),
    ("HTML event attributes", '<ui><button onclick="save"/></ui>', "unknown attribute"),
    ("Numeric booleans", '<ui><switch value="1"/></ui>', "expected true or false; got '1'"),
    ("HTML named entities", '<ui><label>&nbsp;</label></ui>', "Entity 'nbsp' not defined"),
    ("Nested markup in leaves", '<ui><button><label>Hi</label></button></ui>', "component cannot contain child elements"),
    ("Wrong tab children", '<ui><tabbed-content><label/></tabbed-content></ui>', "tabbed-content requires tab-pane children"),
    ("Duplicate IDs", '<ui><label id="a"/><label id="a"/></ui>', "duplicate id"),
)
