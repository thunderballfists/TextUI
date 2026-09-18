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
