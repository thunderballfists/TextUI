import json
from dataclasses import asdict, FrozenInstanceError
from pathlib import Path

import pytest

from textui import AttributeSpec, ComponentRegistry, ComponentSpec, DocumentLoader, integer
from textui.widgets.builtin_widgets import default_component_registry


def test_legacy_integer_converter_has_inspectable_bounds():
    converter = integer(minimum=1, maximum=10)
    assert converter("3") == 3
    assert converter.describe() == {"type": "integer", "minimum": 1, "maximum": 10}


def test_default_attribute_description_retains_optional_default():
    assert AttributeSpec(default="ready").describe() == {
        "type": {"type": "string"}, "required": False, "default": "ready",
    }
    assert AttributeSpec(required=True).describe() == {
        "type": {"type": "string"}, "required": True,
    }


def test_custom_converter_is_not_run_during_metadata_inspection():
    calls = []
    def convert(value):
        calls.append(value)
        return value.upper()
    attribute = AttributeSpec(convert)
    assert attribute.describe()["type"] == {"type": "custom"}
    assert calls == []
    registry = ComponentRegistry()
    registry.register(ComponentSpec("custom", lambda context: None, attributes={"value": attribute}))
    node = DocumentLoader(registry).from_string('<ui><custom value="ready"/></ui>').nodes[0]
    assert node.attributes["value"] == "READY"
    assert calls == ["ready"]


def test_builtin_metadata_is_complete_and_json_serializable():
    specs = default_component_registry().snapshot()
    for tag, spec in specs.items():
        description = spec.describe()
        assert description["tag"] == tag
        assert description["content"]["policy"] == spec.child_policy
        for name, attribute in spec.attributes.items():
            assert attribute.describe()["type"]["type"] != "custom", (tag, name)
        json.dumps(description)


def test_metadata_inspection_does_not_share_mutable_results():
    attribute = AttributeSpec(default=[])
    first = attribute.describe()
    first["default"].append("changed")
    assert attribute.describe()["default"] == []


@pytest.mark.parametrize("character", ["é", "中", "١", "²"])
def test_accelerator_metadata_preserves_unicode_alphanumeric_values(character):
    attribute = default_component_registry().get("tab-pane").attributes["accelerator"]
    assert attribute.converter(character) == character
    assert attribute.describe()["type"]["validation"] == "unicode-alphanumeric-character"


def test_described_types_convert_without_changing_domains():
    from textui.metadata import Bool, Enum, IdRef, Int, Number, Pattern, Text
    for converter, raw, expected in [
        (Text(), "  literal  ", "  literal  "), (Bool(), "false", False),
        (Int(1, 5), "+3", 3), (Enum("a", "b"), "b", "b"),
        (Pattern(r"[a-z]+"), "abc", "abc"), (IdRef("children"), "", ""),
        (Number(True), "1e2", 100.0),
    ]:
        assert converter.convert(raw) == expected
        assert converter(raw) == expected
        json.dumps(converter.describe())
    assert IdRef("children").describe() == {"type": "string", "reference": {"among": "children"}}
    with pytest.raises(FrozenInstanceError):
        Int(1).minimum = 2
    for converter, raw in [(Bool(), "False"), (Int(1, 5), "0"), (Enum("a"), "b"),
                           (Pattern(r"[a-z]+"), "123"), (Number(), "nan"), (Number(True), "0")]:
        with pytest.raises(ValueError):
            converter(raw)


def test_ordered_content_constraints_apply_to_custom_components():
    from textui.content import Children, Count, Only, ElementRef
    from textui import DocumentValidationError
    registry = ComponentRegistry()
    registry.register(ComponentSpec("leaf", lambda context: None))
    registry.register(ComponentSpec("other", lambda context: None))
    registry.register(ComponentSpec("container", lambda context: None, child_policy="widgets",
        content=Children((Count(minimum=1, message="need a child"),
                          Only((ElementRef("leaf"),), message="need leaf children")))))
    loader = DocumentLoader(registry)
    assert len(loader.from_string('<ui><container><leaf/></container></ui>').nodes[0].children) == 1
    for body, message in [('<container/>', 'need a child'), ('<container><other/></container>', 'need leaf children')]:
        with pytest.raises(DocumentValidationError) as caught:
            loader.from_string(f'<ui>{body}</ui>')
        assert caught.value.message == message


def test_custom_unhashable_factory_keeps_permissive_content_and_inspection():
    class Factory:
        __hash__ = None

        def __call__(self, context):
            raise AssertionError("inspection and loading must not construct widgets")

    spec = ComponentSpec("modal", Factory(), child_policy="widgets")
    registry = ComponentRegistry()
    registry.register(spec)
    definition = DocumentLoader(registry).from_string('<ui><modal><modal/></modal></ui>')
    assert len(definition.nodes[0].children) == 1
    assert spec.describe()["content"] == {"policy": "widgets", "rules": []}


def test_native_factory_alias_retains_content_rules_and_describes_them():
    from textui import DocumentValidationError
    from textui.widgets.form_controls import build_option, build_select
    registry = ComponentRegistry()
    spec = ComponentSpec("choice", build_select, child_policy="widgets")
    registry.register(spec)
    registry.register(ComponentSpec("entry", build_option, attributes={"value": AttributeSpec(required=True)}, text_policy="text"))
    assert len(DocumentLoader(registry).from_string('<ui><choice><entry value="one">One</entry></choice></ui>').nodes[0].children) == 1
    with pytest.raises(DocumentValidationError, match="select requires option children"):
        DocumentLoader(registry).from_string('<ui><choice/></ui>')
    assert [rule["rule"] for rule in spec.describe()["content"]["rules"]] == ["count", "only", "named"]


def test_registry_description_lists_common_attributes_and_named_document_rules():
    description = default_component_registry().describe()
    assert description["common_attributes"]["disabled"]["type"]["values"] == ["true", "false"]
    assert {rule["name"] for rule in description["document_rules"]} >= {
        "duplicate-ids", "navigation-targets", "document-accelerators", "data-only-attributes",
    }
    json.dumps(description)
    description["components"][0]["content"]["rules"].append({"changed": True})
    assert default_component_registry().describe()["components"][0]["content"]["rules"] == []


def test_native_widget_subclasses_remain_accepted_at_build_stage():
    from textui import TextUI
    from textui.widgets.split import Pane
    from textui.widgets.builtin_widgets import build_split
    from textui.content import Children
    class CustomPane(Pane):
        pass
    registry = ComponentRegistry()
    registry.register(ComponentSpec("split", build_split, child_policy="widgets",
                                    attributes={"direction": AttributeSpec(default="horizontal")}))
    registry.register(ComponentSpec("custom-pane", lambda context: CustomPane()))
    definition = DocumentLoader(registry).from_string('<ui><split><custom-pane/><custom-pane/></split></ui>')
    assert len(tuple(TextUI(definition).document.compose())) == 1
    with pytest.raises(FrozenInstanceError):
        Children().policy = "none"


def test_split_description_exposes_native_count_and_preserves_build_failure():
    from textui import ComponentBuildError, TextUI
    split = default_component_registry().get("split").describe()
    rule = split["content"]["rules"][0]
    assert rule["rule"] == "native-children"
    assert rule["minimum"] == rule["maximum"] == 2
    assert rule["widget_type"] == "textui.widgets.split.Pane"
    assert rule["phase"] == "build"
    definition = DocumentLoader().from_string('<ui><split><pane/></split></ui>')
    with pytest.raises(ComponentBuildError, match="split requires exactly two pane children"):
        tuple(TextUI(definition).document.compose())


CASES = json.loads((Path(__file__).parent / "fixtures" / "registry_structure.json").read_text())


@pytest.mark.parametrize("case", CASES)
def test_structural_metadata_preserves_baseline_diagnostic_and_stage(case):
    from textui import TextUI, TextUIError
    with pytest.raises(TextUIError) as caught:
        definition = DocumentLoader().from_string(case["markup"], source_name="contract.ui")
        if case["stage"] == "build":
            tuple(TextUI(definition).document.compose())
    error = caught.value
    actual = {"class": type(error).__name__, "message": error.message,
              "attribute": error.attribute, "value": error.value,
              "location": asdict(error.location) if error.location else None}
    assert actual == case["expected"]
