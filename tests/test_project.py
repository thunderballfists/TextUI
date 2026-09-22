from pathlib import Path

import pytest

from textui import DocumentValidationError
from textui.project import ProjectSource
from textui.widgets.builtin_widgets import default_component_registry


def test_project_discovers_resources_and_nested_includes_from_declaring_file(tmp_path: Path, monkeypatch):
    (tmp_path / "views").mkdir()
    (tmp_path / "views" / "parts").mkdir()
    (tmp_path / "app.ui").write_text(
        '<ui><style src="shell.tcss"/><script src="controller.py"/>'
        '<vertical id="main"><include src="views/workspace.ui"/></vertical></ui>',
        encoding="utf-8",
    )
    (tmp_path / "shell.tcss").write_text("Label { color: red; }", encoding="utf-8")
    (tmp_path / "controller.py").write_text("", encoding="utf-8")
    (tmp_path / "views" / "workspace.ui").write_text(
        '<ui><include src="parts/status.ui"/></ui>', encoding="utf-8"
    )
    (tmp_path / "views" / "parts" / "status.ui").write_text(
        '<ui><label id="status">Ready</label></ui>', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path.parent)

    source = ProjectSource.discover(tmp_path / "app.ui")
    document = source.lower(default_component_registry())

    assert source.scripts == (tmp_path / "controller.py",)
    assert document.styles[0].content == "Label { color: red; }"
    assert document.styles[0].location.source == str(tmp_path / "shell.tcss")
    status = document.nodes[0].children[0]
    assert status.common["id"] == "status"
    assert status.location.source == str(tmp_path / "views" / "parts" / "status.ui")


def test_project_detects_include_cycles_with_chain(tmp_path: Path):
    entry = tmp_path / "app.ui"
    child = tmp_path / "child.ui"
    entry.write_text('<ui><include src="child.ui"/></ui>', encoding="utf-8")
    child.write_text('<ui><include src="app.ui"/></ui>', encoding="utf-8")

    with pytest.raises(DocumentValidationError, match="include cycle") as caught:
        ProjectSource.discover(entry)
    assert "app.ui" in str(caught.value)
    assert "child.ui" in str(caught.value)


def test_duplicate_ids_are_checked_across_included_files(tmp_path: Path):
    (tmp_path / "app.ui").write_text(
        '<ui><label id="same">Entry</label><include src="child.ui"/></ui>', encoding="utf-8"
    )
    (tmp_path / "child.ui").write_text(
        '<ui><label id="same">Child</label></ui>', encoding="utf-8"
    )
    source = ProjectSource.discover(tmp_path / "app.ui")

    with pytest.raises(DocumentValidationError, match="duplicate id") as caught:
        source.lower(default_component_registry())
    assert caught.value.location.source.endswith("child.ui")


@pytest.mark.parametrize("child", ['<style>Label { color: red; }</style>', '<script src="x.py"/>'])
def test_includes_cannot_contain_styles_or_scripts(tmp_path: Path, child: str):
    (tmp_path / "app.ui").write_text('<ui><include src="child.ui"/></ui>', encoding="utf-8")
    (tmp_path / "child.ui").write_text(f"<ui>{child}</ui>", encoding="utf-8")

    with pytest.raises(DocumentValidationError, match="entry"):
        ProjectSource.discover(tmp_path / "app.ui")


def test_script_discovery_does_not_execute_python(tmp_path: Path):
    (tmp_path / "app.ui").write_text('<ui><script src="controller.py"/></ui>', encoding="utf-8")
    (tmp_path / "controller.py").write_text('raise RuntimeError("executed")', encoding="utf-8")

    assert ProjectSource.discover(tmp_path / "app.ui").scripts == (tmp_path / "controller.py",)


def test_sourced_and_inline_styles_keep_entry_order(tmp_path: Path):
    (tmp_path / "app.ui").write_text(
        '<ui><style>Label { color: red; }</style><style src="later.tcss"/>'
        '<style>Label { color: blue; }</style><label>Hi</label></ui>', encoding="utf-8"
    )
    (tmp_path / "later.tcss").write_text("Label { color: green; }", encoding="utf-8")

    document = ProjectSource.discover(tmp_path / "app.ui").lower(default_component_registry())
    assert [style.index for style in document.styles] == [0, 1, 2]
    assert ["red" in document.styles[0].content, "green" in document.styles[1].content, "blue" in document.styles[2].content] == [True] * 3
    assert document.styles[1].location.source == str(tmp_path / "later.tcss")


def test_project_style_preset_keeps_entry_order_with_project_tcss(tmp_path: Path):
    (tmp_path / "app.ui").write_text(
        '<ui><style preset="compact"/><style>Button { padding: 0 2; }</style><button>Save</button></ui>',
        encoding="utf-8",
    )

    document = ProjectSource.discover(tmp_path / "app.ui").lower(default_component_registry())

    assert [style.index for style in document.styles] == [0, 1]
    assert "padding: 0 1" in document.styles[0].content
    assert "padding: 0 2" in document.styles[1].content


def test_same_script_declared_twice_is_loaded_once(tmp_path: Path):
    script = tmp_path / "controller.py"
    script.write_text("", encoding="utf-8")
    (tmp_path / "app.ui").write_text(
        '<ui><script src="controller.py"/><script src="controller.py"/></ui>', encoding="utf-8"
    )

    assert ProjectSource.discover(tmp_path / "app.ui").scripts == (script,)


def test_project_expands_component_properties_slots_and_private_ids(tmp_path: Path):
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "card.ui").write_text(
        "<component><props><prop name=\"name\" required=\"true\"/>"
        "<prop name=\"status\" default=\"Unknown\"/></props>"
        "<vertical id=\"card\" class=\"card\"><label id=\"title\">{name}</label>"
        "<label>{status}</label><slot name=\"actions\"><button>Details</button></slot>"
        "</vertical></component>",
        encoding="utf-8",
    )
    (tmp_path / "app.ui").write_text(
        "<ui><component src=\"components/card.ui\" as=\"agent-card\"/>"
        "<agent-card id=\"alpha\" name=\"Alpha\" class=\"selected\" autofocus=\"true\">"
        "<slot name=\"actions\"><button on-pressed=\"open_alpha\">Open</button></slot>"
        "</agent-card><agent-card id=\"beta\" name=\"Beta\"/></ui>",
        encoding="utf-8",
    )

    document = ProjectSource.discover(tmp_path / "app.ui").lower(default_component_registry())
    alpha, beta = document.nodes
    assert alpha.common["id"] == "alpha"
    assert alpha.common["classes"] == ("card", "selected")
    assert alpha.common["autofocus"] is True
    assert alpha.children[0].common["id"].startswith("__component_1_")
    assert alpha.children[0].text == "Alpha"
    assert alpha.children[1].text == "Unknown"
    assert alpha.children[2].text == "Open"
    assert alpha.children[2].events == {"pressed": "open_alpha"}
    assert beta.common["id"] == "beta"
    assert beta.children[0].common["id"] != alpha.children[0].common["id"]


@pytest.mark.parametrize(
    ("markup", "message"),
    [
        ("<agent-card extra=\"value\"/>", "unknown component property"),
        ("<agent-card/>", "required component property is missing"),
        ("<agent-card name=\"A\"><slot name=\"missing\"/></agent-card>", "unknown component slot"),
    ],
)
def test_component_calls_validate_properties_and_slots(tmp_path: Path, markup: str, message: str):
    (tmp_path / "card.ui").write_text(
        "<component><props><prop name=\"name\" required=\"true\"/></props>"
        "<vertical><label>{name}</label><slot name=\"actions\"/></vertical></component>",
        encoding="utf-8",
    )
    (tmp_path / "app.ui").write_text(
        f'<ui><component src="card.ui" as="agent-card"/>{markup}</ui>', encoding="utf-8"
    )

    with pytest.raises(DocumentValidationError, match=message):
        ProjectSource.discover(tmp_path / "app.ui").lower(default_component_registry())


def test_component_import_cycles_are_reported(tmp_path: Path):
    (tmp_path / "a.ui").write_text(
        '<component><component src="b.ui" as="b-card"/><b-card/></component>', encoding="utf-8"
    )
    (tmp_path / "b.ui").write_text(
        '<component><component src="a.ui" as="a-card"/><a-card/></component>', encoding="utf-8"
    )
    (tmp_path / "app.ui").write_text(
        '<ui><component src="a.ui" as="a-card"/><a-card/></ui>', encoding="utf-8"
    )

    with pytest.raises(DocumentValidationError, match="component import cycle") as caught:
        ProjectSource.discover(tmp_path / "app.ui")
    assert "a.ui" in str(caught.value)
    assert "b.ui" in str(caught.value)


def test_component_definitions_reject_runtime_directives(tmp_path: Path):
    (tmp_path / "card.ui").write_text(
        '<component><script src="controller.py"/><vertical/></component>', encoding="utf-8"
    )
    (tmp_path / "app.ui").write_text(
        '<ui><component src="card.ui" as="agent-card"/></ui>', encoding="utf-8"
    )

    with pytest.raises(DocumentValidationError, match="script is not allowed"):
        ProjectSource.discover(tmp_path / "app.ui")


def test_included_files_cannot_declare_component_imports(tmp_path: Path):
    (tmp_path / "parts").mkdir()
    (tmp_path / "app.ui").write_text('<ui><include src="parts/view.ui"/></ui>', encoding="utf-8")
    (tmp_path / "parts" / "view.ui").write_text(
        '<ui><component src="card.ui" as="agent-card"/></ui>', encoding="utf-8"
    )

    with pytest.raises(DocumentValidationError, match="entry root"):
        ProjectSource.discover(tmp_path / "app.ui")


def test_component_definitions_reject_duplicate_default_slots(tmp_path: Path):
    (tmp_path / "card.ui").write_text(
        '<component><vertical><slot><label>One</label></slot><slot><label>Two</label></slot></vertical></component>',
        encoding="utf-8",
    )
    (tmp_path / "app.ui").write_text(
        '<ui><component src="card.ui" as="agent-card"/><agent-card/></ui>', encoding="utf-8"
    )

    with pytest.raises(DocumentValidationError, match="unique optional names"):
        ProjectSource.discover(tmp_path / "app.ui").lower(default_component_registry())


def test_component_rewrites_internal_id_references(tmp_path: Path):
    (tmp_path / "tabs.ui").write_text(
        '<component><tabbed-content initial="home"><tab-pane id="home" title="Home"><label>Ready</label></tab-pane></tabbed-content></component>',
        encoding="utf-8",
    )
    (tmp_path / "app.ui").write_text(
        '<ui><component src="tabs.ui" as="app-tabs"/><app-tabs/></ui>', encoding="utf-8"
    )

    document = ProjectSource.discover(tmp_path / "app.ui").lower(default_component_registry())
    assert document.nodes[0].attributes["initial"] == "__component_1_home"
    assert document.nodes[0].children[0].common["id"] == "__component_1_home"


def test_slot_children_expand_in_the_callers_component_scope(tmp_path: Path):
    (tmp_path / "leaf.ui").write_text('<component><label>Leaf</label></component>', encoding="utf-8")
    (tmp_path / "wrapper.ui").write_text(
        '<component><vertical><slot name="body"/></vertical></component>', encoding="utf-8"
    )
    (tmp_path / "app.ui").write_text(
        '<ui><component src="leaf.ui" as="x-leaf"/><component src="wrapper.ui" as="x-wrapper"/>'
        '<x-wrapper><slot name="body"><x-leaf/></slot></x-wrapper></ui>',
        encoding="utf-8",
    )

    document = ProjectSource.discover(tmp_path / "app.ui").lower(default_component_registry())
    assert document.nodes[0].children[0].spec.tag == "label"


@pytest.mark.parametrize(
    ("template_slot", "call_slot"),
    [
        ("<slot name=\"body\">Text<label>Fallback</label></slot>", ""),
        ("<slot name=\"body\"/>", "<slot name=\"body\">Text<label>Caller</label></slot>"),
    ],
)
def test_component_slots_reject_nonwhitespace_text(tmp_path: Path, template_slot: str, call_slot: str):
    (tmp_path / "card.ui").write_text(
        f"<component><vertical>{template_slot}</vertical></component>", encoding="utf-8"
    )
    (tmp_path / "app.ui").write_text(
        f'<ui><component src="card.ui" as="agent-card"/><agent-card>{call_slot}</agent-card></ui>',
        encoding="utf-8",
    )

    with pytest.raises(DocumentValidationError, match="slot text is not allowed"):
        ProjectSource.discover(tmp_path / "app.ui").lower(default_component_registry())
