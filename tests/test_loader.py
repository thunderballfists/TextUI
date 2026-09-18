from __future__ import annotations

from pathlib import Path

import pytest

import textui


def load(markup: str):
    return textui.DocumentLoader().from_string(markup)


def test_public_loader_api_is_available():
    assert hasattr(textui, "DocumentLoader"), "The new loader API is missing"
    assert hasattr(textui, "Document"), "The immutable Document API is missing"


def test_false_and_classes_are_normalized_without_constructing_widgets():
    document = load(
        '<ui><checkbox id="notify" class="one two one" value="false">Notify</checkbox></ui>'
    )

    node = document.nodes[0]
    assert node.attributes["value"] is False
    assert node.common["classes"] == ("one", "two")
    assert node.text == "Notify"


def test_loading_does_not_construct_registered_components():
    calls = 0

    def build(context):
        nonlocal calls
        calls += 1
        raise AssertionError("loading must not invoke factories")

    registry = textui.ComponentRegistry()
    registry.register(
        textui.ComponentSpec(tag="counter", factory=build, text_policy="text")
    )

    document = textui.DocumentLoader(registry).from_string("<ui><counter>text</counter></ui>")

    assert document.nodes[0].text == "text"
    assert calls == 0


@pytest.mark.parametrize(
    "markup",
    [
        "<page />",
        '<ui bad="value" />',
        "<ui><unknown /></ui>",
        '<ui><label unsupported="value">text</label></ui>',
        '<ui><label on-pressed="save">text</label></ui>',
        '<ui><vertical id="same"><label id="same">x</label></vertical></ui>',
        '<ui><label id="">text</label></ui>',
        '<ui><checkbox value="maybe">text</checkbox></ui>',
        '<ui><input max-length="0" /></ui>',
        '<ui><button variant="purple">text</button></ui>',
        '<ui><style lang="tcss">x { color: red; }</style></ui>',
        "<ui><label>one<strong>two</strong></label></ui>",
        "<ui><input>non-empty</input></ui>",
        "<ui><vertical>non-empty</vertical></ui>",
        "<ui><label>one</label>tail</ui>",
        "<ui><?invalid value?><label>text</label></ui>",
        "<?invalid value?><ui><label>text</label></ui>",
        "<!DOCTYPE ui><ui><label>text</label></ui>",
        "<ui><label>&unknown;</label></ui>",
        "<ui><label></ui>",
        '<ui xmlns="urn:bad"><label>text</label></ui>',
        "<ui><bad_name /></ui>",
    ],
)
def test_loader_rejects_invalid_document_grammar(markup):
    with pytest.raises((textui.DocumentSyntaxError, textui.DocumentValidationError)):
        load(markup)


def test_missing_required_custom_attribute_has_element_context():
    registry = textui.ComponentRegistry()
    registry.register(
        textui.ComponentSpec(
            tag="status",
            factory=lambda context: None,
            attributes={"code": textui.AttributeSpec(required=True)},
        )
    )

    with pytest.raises(textui.DocumentValidationError) as caught:
        textui.DocumentLoader(registry).from_string("<ui><status /></ui>", source_name="form.xml")

    assert caught.value.location.source == "form.xml"
    assert caught.value.location.tag == "status"
    assert caught.value.attribute == "code"


def test_comments_and_utf8_declaration_are_permitted_and_styles_are_verbatim():
    markup = """<?xml version='1.0' encoding='UTF-8'?>
<ui><!-- ignored --><style><![CDATA[\n.x { color: red; }\n]]></style><label>Hello <!-- comment --> world</label></ui>"""

    document = load(markup)

    assert document.styles[0].content == "\n.x { color: red; }\n"
    assert document.nodes[0].text == "Hello world"


def test_style_must_be_direct_child_and_cannot_have_children_or_nonwhitespace_tail():
    for markup in (
        "<ui><vertical><style>x { color: red; }</style></vertical></ui>",
        "<ui><style><label>bad</label></style></ui>",
        "<ui><style>x { color: red; }</style>tail</ui>",
    ):
        with pytest.raises(textui.DocumentValidationError):
            load(markup)


def test_file_and_string_loading_match_and_missing_file_has_source_context(tmp_path: Path):
    path = tmp_path / "form.xml"
    markup = "<?xml version='1.0' encoding='UTF-8'?><ui><label>Hi</label></ui>"
    path.write_text(markup, encoding="utf-8")

    from_file = textui.DocumentLoader().from_file(path)
    from_string = textui.DocumentLoader().from_string(markup, source_name=str(path.resolve()))

    assert from_file == from_string
    with pytest.raises(textui.DocumentLoadError) as caught:
        textui.DocumentLoader().from_file(tmp_path / "missing.xml")
    assert "missing.xml" in caught.value.location.source
    assert caught.value.__cause__ is not None


def test_nodes_documents_and_locations_are_immutable():
    document = load('<ui><button id="save" on-pressed="save_it">Save</button></ui>')
    node = document.nodes[0]

    assert node.events == {"pressed": "save_it"}
    with pytest.raises(TypeError):
        node.attributes["variant"] = "error"
    with pytest.raises(Exception):
        node.text = "Other"
