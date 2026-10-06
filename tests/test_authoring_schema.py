import ast
import json
from pathlib import Path
import re

from lxml import etree
import pytest

from textui import DocumentLoader, TextUIError
from textui.authoring.facts import EXAMPLES, MISTAKES
from textui.static_check import check_static


ROOT = Path(__file__).resolve().parents[1]
CORPUS = json.loads((ROOT / "tests/fixtures/registry_structure.json").read_text())
EXCEPTIONS = json.loads((ROOT / "tests/fixtures/schema_exceptions.json").read_text())
STRICT = etree.XMLSchema(etree.parse(str(ROOT / "spec/textui.xsd")))
AUTHORING = etree.XMLSchema(etree.parse(str(ROOT / "spec/textui-authoring.xsd")))


def expanded_markup(document):
    """Serialize immutable lowered nodes, not widgets, for the strict profile."""
    root = etree.Element("ui")

    def literal(value):
        return str(value).lower() if isinstance(value, bool) else str(value)

    def add(parent, node):
        element = etree.SubElement(parent, node.spec.tag)
        element.text = node.text
        for name, value in node.attributes.items():
            if value is not None:
                element.set(name, literal(value))
        if node.common["id"] is not None:
            element.set("id", node.common["id"])
        if node.common["classes"]:
            element.set("class", " ".join(node.common["classes"]))
        if node.common["style"] is not None:
            element.set("style", node.common["style"])
        for name in ("disabled", "autofocus"):
            if node.common[name]:
                element.set(name, "true")
        for name, value in node.events.items():
            element.set(f"on-{name}", value)
        for child in node.children:
            add(element, child)

    for node in document.nodes:
        add(root, node)
    return root


@pytest.mark.parametrize("index,case", list(enumerate(CORPUS)))
def test_schema_agrees_with_structural_contract_except_explicit_rules(tmp_path, index, case):
    markup = case["markup"]
    if case["stage"] == "load":
        with pytest.raises(TextUIError) as caught:
            DocumentLoader().from_string(markup)
        assert caught.value.message == case["expected"]["message"]
    else:
        # These known native-type checks are deferred by the ordinary loader.
        DocumentLoader().from_string(markup)
    entry = tmp_path / "app.ui"
    entry.write_text(markup, encoding="utf-8")
    with pytest.raises(TextUIError):
        check_static(entry)
    accepted = STRICT.validate(etree.fromstring(markup.encode()))
    assert accepted == (str(index) in EXCEPTIONS), (index, STRICT.error_log)
    if accepted:
        assert EXCEPTIONS[str(index)].strip()


def test_schema_allowlist_has_no_unused_cases():
    assert {int(index) for index in EXCEPTIONS} <= set(range(len(CORPUS)))


@pytest.mark.parametrize("markup", [
    '<ui bad="x"/>', '<ui><unknown-widget/></ui>', '<ui><input max-length=" 2"/></ui>',
    '<ui><input max-length="²"/></ui>', '<ui><input max-length="++2"/></ui>',
    '<ui><switch value=" false "/></ui>', '<ui><switch value="0"/></ui>',
    '<ui><button variant="Primary"/></ui>', '<ui><list/></ui>',
    '<ui><data-table><column key="x" autofocus="false"/></data-table></ui>',
])
def test_strict_schema_rejects_lexical_and_attribute_mistakes(markup):
    with pytest.raises(TextUIError):
        DocumentLoader().from_string(markup)
    assert not STRICT.validate(etree.fromstring(markup.encode()))


def test_documented_numeric_schema_limit_does_not_narrow_valid_unicode():
    # The lexical schema accepts negative literals; metadata/runtime checks
    # enforce bounds. Python and XSD string domains both retain Arabic digits.
    markup = '<ui><input max-length="-1"/></ui>'
    assert STRICT.validate(etree.fromstring(markup.encode()))
    with pytest.raises(TextUIError, match="integer >= 1"):
        DocumentLoader().from_string(markup)


@pytest.mark.parametrize("markup", [
    '<ui/>', '<ui><label>Hello</label><switch value="true"/></ui>',
    '<ui><split><pane/><pane/></split></ui>',
    '<ui><tabbed-content initial="one"><tab-pane id="one" title="One"/></tabbed-content></ui>',
    '<ui><header><right/><left/><center/></header></ui>',
    '<ui><data-table><column key="a"/><row key="r"><cell>A</cell></row></data-table></ui>',
    '<ui><tree label="Root"><tree-node key="x" label="X"/></tree></ui>',
    '<ui><input max-length="+١٠"/></ui>',
])
def test_valid_builtin_corpus_agrees(tmp_path, markup):
    DocumentLoader().from_string(markup)
    assert STRICT.validate(etree.fromstring(markup.encode())), STRICT.error_log
    entry = tmp_path / "app.ui"
    entry.write_text(markup, encoding="utf-8")
    check_static(entry)


@pytest.mark.parametrize("path", sorted((ROOT / "examples").rglob("*.ui")))
def test_every_raw_example_and_its_expanded_project_validate(path):
    assert AUTHORING.validate(etree.parse(str(path))), (path, AUTHORING.error_log)
    relative = str(path.relative_to(ROOT))
    owners = {
        "examples/components/agent-card.ui": "examples/components/app.ui",
        "examples/showcase/components/agent-card.ui": "examples/showcase/app.ui",
        "examples/showcase/views/overview.ui": "examples/showcase/app.ui",
        "examples/project/views/form.ui": "examples/project/app.ui",
    }
    document = check_static(ROOT / owners.get(relative, relative))
    assert STRICT.validate(expanded_markup(document)), (path, STRICT.error_log)


@pytest.mark.parametrize("title,markup,message", MISTAKES)
def test_llm_common_mistakes_are_pinned_to_loader_diagnostics(title, markup, message):
    with pytest.raises(TextUIError) as caught:
        DocumentLoader().from_string(markup)
    assert message in caught.value.message


def test_schema_profiles_do_not_claim_to_resolve_aliases(tmp_path):
    markup = '<ui><unknown-card/></ui>'
    assert not STRICT.validate(etree.fromstring(markup.encode()))
    assert AUTHORING.validate(etree.fromstring(markup.encode()))
    entry = tmp_path / "app.ui"
    entry.write_text(markup, encoding="utf-8")
    with pytest.raises(TextUIError, match="unknown component"):
        check_static(entry)


def test_component_placeholders_are_checked_after_substitution(tmp_path):
    template = '<component><props><prop name="length" required="true"/></props><input max-length="{length}"/></component>'
    assert AUTHORING.validate(etree.fromstring(template.encode()))
    (tmp_path / "field.ui").write_text(template, encoding="utf-8")
    entry = tmp_path / "app.ui"
    entry.write_text('<ui><component src="field.ui" as="field"/><field length="5"/></ui>', encoding="utf-8")
    assert STRICT.validate(expanded_markup(check_static(entry)))
    entry.write_text('<ui><component src="field.ui" as="field"/><field length="bad"/></ui>', encoding="utf-8")
    with pytest.raises(TextUIError, match="expected a base-10 integer"):
        check_static(entry)


@pytest.mark.parametrize("alias", ["input", "tree", "tab-pane"])
def test_authoring_profile_accepts_aliases_that_shadow_builtin_attributes(tmp_path, alias):
    (tmp_path / "card.ui").write_text(
        '<component><props><prop name="caption" required="true"/></props>'
        '<label>{caption}</label></component>', encoding="utf-8",
    )
    markup = f'<ui><component src="card.ui" as="{alias}"/><{alias} caption="Hi"/></ui>'
    entry = tmp_path / "app.ui"
    entry.write_text(markup, encoding="utf-8")
    document = check_static(entry)
    assert document.nodes[0].spec.tag == "label"
    assert document.nodes[0].text == "Hi"
    assert AUTHORING.validate(etree.fromstring(markup.encode())), AUTHORING.error_log
    assert STRICT.validate(expanded_markup(document)), STRICT.error_log


@pytest.mark.parametrize("alias", ["input", "button"])
def test_authoring_profile_accepts_aliases_that_shadow_builtin_children(tmp_path, alias):
    (tmp_path / "card.ui").write_text('<component><vertical><slot/></vertical></component>', encoding="utf-8")
    markup = f'<ui><component src="card.ui" as="{alias}"/><vertical><{alias}><label>Hi</label></{alias}></vertical></ui>'
    entry = tmp_path / "app.ui"
    entry.write_text(markup, encoding="utf-8")
    assert STRICT.validate(expanded_markup(check_static(entry))), STRICT.error_log
    assert AUTHORING.validate(etree.fromstring(markup.encode())), AUTHORING.error_log


def test_permissive_profile_leaves_widget_literals_to_static_check(tmp_path):
    markup = '<ui><switch value="wrong"/></ui>'
    assert AUTHORING.validate(etree.fromstring(markup.encode()))
    entry = tmp_path / "app.ui"
    entry.write_text(markup, encoding="utf-8")
    with pytest.raises(TextUIError, match="expected true or false"):
        check_static(entry)


def test_strict_style_preset_schema_preserves_known_values(tmp_path):
    for preset in ("compact", "borders"):
        markup = f'<ui><style preset="{preset}"/></ui>'
        assert STRICT.validate(etree.fromstring(markup.encode())), STRICT.error_log
        DocumentLoader().from_string(markup)
    markup = '<ui><style preset="typo"/></ui>'
    assert not STRICT.validate(etree.fromstring(markup.encode()))
    with pytest.raises(TextUIError, match="unknown style preset"):
        DocumentLoader().from_string(markup)
    for schema in (STRICT, AUTHORING):
        # Global declarations provide metadata even when a permissive body's
        # dynamic aliases prevent applying that metadata as validation rules.
        assert not schema.validate(etree.fromstring(b'<style preset="typo"/>'))


@pytest.mark.parametrize("container,fragment", [
    (None, '<label>Hi</label>'),
    ("vertical", '<label>Hi</label>'),
    ("split", '<pane/><pane/>'),
    ("select", '<option value="one">One</option>'),
])
def test_include_projects_use_authoring_profile_and_expanded_strict_schema(tmp_path, container, fragment):
    (tmp_path / "body.ui").write_text(f'<ui>{fragment}</ui>', encoding="utf-8")
    include = '<include src="body.ui"/>'
    body = f'<{container}>{include}</{container}>' if container else include
    markup = f'<ui>{body}</ui>'
    entry = tmp_path / "app.ui"
    entry.write_text(markup, encoding="utf-8")
    assert AUTHORING.validate(etree.fromstring(markup.encode())), AUTHORING.error_log
    assert not STRICT.validate(etree.fromstring(markup.encode()))
    assert STRICT.validate(expanded_markup(check_static(entry))), STRICT.error_log


def test_readme_examples_validate_with_explicit_custom_registry_exception(tmp_path):
    readme = (ROOT / "README.md").read_text()
    markup_examples = []
    for language, code in re.findall(r"```(\w+)\n(.*?)```", readme, re.S):
        if language == "python":
            for node in ast.walk(ast.parse(code)):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.strip().startswith("<ui>"):
                    markup_examples.append(node.value)
        elif language == "xml":
            markup_examples.append(code if code.strip().startswith("<ui>") else f"<ui>{code}</ui>")
    assert len(markup_examples) >= 4
    (tmp_path / "components").mkdir()
    (tmp_path / "components/agent-card.ui").write_text(EXAMPLES["examples/components/agent-card.ui"], encoding="utf-8")
    for markup in markup_examples:
        entry = tmp_path / "app.ui"
        entry.write_text(markup, encoding="utf-8")
        if "count-label" in markup:
            # README explicitly registers this Python extension; built-in-only
            # schema/static checking cannot infer controller registrations.
            from textui import AttributeSpec, ComponentSpec, integer
            from textui.widgets.builtin_widgets import default_component_registry
            registry = default_component_registry()
            registry.register(ComponentSpec("count-label", lambda context: None, attributes={"count": AttributeSpec(integer(minimum=0), default=0)}))
            DocumentLoader(registry).from_string(markup)
            assert AUTHORING.validate(etree.fromstring(markup.encode()))
            with pytest.raises(TextUIError, match="unknown component 'count-label'"):
                check_static(entry)
        else:
            assert AUTHORING.validate(etree.fromstring(markup.encode())), AUTHORING.error_log
            assert STRICT.validate(expanded_markup(check_static(entry))), STRICT.error_log


def test_llm_canonical_examples_validate(tmp_path):
    reference = (ROOT / "docs/llm-reference.md").read_text().split("## Common mistakes")[0]
    samples = re.findall(r"```xml\n(.*?)```", reference, re.S)
    assert len(samples) == len(EXAMPLES)
    for relative, markup in EXAMPLES.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markup, encoding="utf-8")
    (tmp_path / "examples/components/controller.py").write_text("raise RuntimeError('must not run')", encoding="utf-8")
    for markup in samples:
        assert AUTHORING.validate(etree.fromstring(markup.encode())), AUTHORING.error_log
    for relative in ("examples/sample_markup.xml", "examples/form.xml", "examples/components/app.ui"):
        assert STRICT.validate(expanded_markup(check_static(tmp_path / relative))), STRICT.error_log
