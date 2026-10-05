import json
import pytest
from textual.app import App
from textual.widget import Widget

from textui.__main__ import main


def test_static_check_never_executes_controllers_or_constructs_widgets(tmp_path, monkeypatch, capsys):
    marker = tmp_path / "executed"
    (tmp_path / "controller.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\nraise RuntimeError('executed')\n",
        encoding="utf-8",
    )
    (tmp_path / "card.ui").write_text(
        '<component><props><prop name="title" required="true"/></props>'
        '<vertical><label>{title}</label><button on-pressed="missing_action">OK</button></vertical></component>',
        encoding="utf-8",
    )
    (tmp_path / "body.ui").write_text('<ui><card title="Hi"/></ui>', encoding="utf-8")
    entry = tmp_path / "app.ui"
    entry.write_text(
        '<ui><script src="controller.py"/><component src="card.ui" as="card"/>'
        '<include src="body.ui"/></ui>', encoding="utf-8",
    )

    def forbidden(*args, **kwargs):
        pytest.fail("static checking constructed an App or Widget")

    monkeypatch.setattr(App, "__init__", forbidden)
    monkeypatch.setattr(Widget, "__init__", forbidden)
    assert main(["check", "--static", "--format", "json", str(entry)]) == 0
    assert json.loads(capsys.readouterr().out) == []
    assert not marker.exists()


def test_static_json_reports_original_include_location(tmp_path, capsys):
    included = tmp_path / "bad.ui"
    included.write_text('<ui>\n<input max-length="no"/>\n</ui>', encoding="utf-8")
    entry = tmp_path / "app.ui"
    entry.write_text('<ui><include src="bad.ui"/></ui>', encoding="utf-8")
    assert main(["check", "--static", "--format", "json", str(entry)]) == 1
    output = capsys.readouterr()
    assert not output.err
    assert json.loads(output.out) == [{
        "file": str(included), "line": 2, "column": None,
        "element": "input", "attribute": "max-length",
        "message": "expected a base-10 integer; got 'no'",
    }]


@pytest.mark.parametrize("markup,message", [
    ('<ui><split><pane/></split></ui>', "split requires exactly two pane children"),
    ('<ui><split><pane/><label/></split></ui>', "split requires exactly two pane children"),
    ('<ui><nav><label/></nav></ui>', "nav requires nav-item children"),
    ('<ui><progress-bar total="2" progress="3"/></ui>', "progress cannot exceed total"),
])
def test_static_checks_compound_and_native_children(tmp_path, capsys, markup, message):
    entry = tmp_path / "app.ui"
    entry.write_text(markup, encoding="utf-8")
    assert main(["check", "--static", str(entry)]) == 1
    assert message in capsys.readouterr().err


def test_static_private_component_tabs_and_list_patterns(tmp_path, capsys):
    (tmp_path / "card.ui").write_text(
        '<component><props><prop name="pattern" required="true"/></props>'
        '<tabbed-content initial="first"><tab-pane id="first" title="First" '
        'accelerator="x" accelerator-scope="document"><list item-label="{pattern}"/>'
        '</tab-pane></tabbed-content></component>', encoding="utf-8",
    )
    entry = tmp_path / "app.ui"
    entry.write_text('<ui><component src="card.ui" as="card"/><card pattern="{name}"/></ui>', encoding="utf-8")
    assert main(["check", "--static", str(entry)]) == 0
    assert "Checked" in capsys.readouterr().out


@pytest.mark.parametrize("content", [None, '<ui><label></ui>', '<?xml-model href="textui.xsd"?><ui/>'])
def test_static_file_and_parse_errors_are_json(tmp_path, capsys, content):
    entry = tmp_path / "app.ui"
    if content is not None:
        entry.write_text(content, encoding="utf-8")
    assert main(["check", "--static", "--format", "json", str(entry)]) == 1
    records = json.loads(capsys.readouterr().out)
    assert len(records) == 1
    assert records[0]["file"] == str(entry)
    assert set(records[0]) == {"file", "line", "column", "element", "attribute", "message"}


def test_json_requires_static_mode(tmp_path):
    with pytest.raises(SystemExit) as caught:
        main(["check", "--format", "json", str(tmp_path / "app.ui")])
    assert caught.value.code == 2
