"""Exercise check through the CLI and real trusted project preparation."""

from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from textui.__main__ import main
from textui.project import ProjectSource
from textui.project_app import ProjectApp


def invoke(*args):
    try:
        return main(args)
    except SystemExit as error:
        return error.code


def write_project(tmp_path, files):
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return tmp_path / "app.ui"


def test_check_runs_setup_and_close_without_mounting_or_invoking_callbacks(tmp_path, monkeypatch, capsys):
    entry = write_project(tmp_path, {
        "app.ui": '<ui><script src="controller.py"/><custom-label/><input on-changed="changed"/><modal id="help"><custom-label/></modal></ui>',
        "controller.py": '''
import asyncio
from pathlib import Path
from textual.widgets import Label
from textui import ComponentSpec, action, every

def record(value):
    with Path(__file__).with_suffix(".events").open("a") as output:
        output.write(value + "\\n")

record("load")
class UnmountedLabel(Label):
    def on_mount(self):
        raise AssertionError("check must not mount widgets")

def build(context):
    record("build:" + window.phase)
    return UnmountedLabel("custom")

async def on_setup():
    await asyncio.sleep(0)
    record("setup")
    window.registry.register(ComponentSpec(tag="custom-label", factory=build))

@action
def changed(context):
    raise AssertionError("check must not dispatch actions")

def on_ready():
    raise AssertionError("check must not become ready")

def on_resize(width, height):
    raise AssertionError("check must not resize")

@every(0.01)
def tick():
    raise AssertionError("check must not start timers")

async def on_close():
    await asyncio.sleep(0)
    record("close:" + window.phase)
''',
    })
    monkeypatch.chdir(tmp_path.parent)

    assert invoke("check", str(entry)) == 0
    output = capsys.readouterr()
    assert str(entry) in output.out
    assert output.err == ""
    assert (tmp_path / "controller.events").read_text().splitlines() == [
        "load", "setup", "build:bound", "build:bound", "close:closing",
    ]


@pytest.mark.parametrize("files,source,diagnostic", [
    ({"app.ui": "<ui><label></ui>"}, "app.ui", "Opening and ending tag mismatch"),
    ({"app.ui": "<ui>\n<unknown/>\n</ui>"}, "app.ui:2", "unknown"),
    ({"app.ui": '<ui>\n<button on-pressed="missing"/>\n</ui>'}, "app.ui:2", "missing"),
    ({"app.ui": '<ui><style src="missing.tcss"/></ui>'}, "app.ui:1", "missing.tcss"),
    ({"app.ui": '<ui><script src="missing.py"/></ui>'}, "app.ui:1", "missing.py"),
    ({"app.ui": '<ui><include src="view.ui"/></ui>', "view.ui": "<ui>\n<unknown/>\n</ui>"}, "view.ui:2", "unknown"),
    ({"app.ui": '<ui><style src="app.tcss"/><label/></ui>', "app.tcss": "Label {\n    not-a-property: red;\n}"}, "app.tcss:2", "not-a-property"),
    ({"app.ui": '<ui>\n<label style="not-a-property: red;"/>\n</ui>'}, "app.ui:2", "not-a-property"),
    ({"app.ui": '<ui>\n<modal id="help"><label style="not-a-property: red;"/></modal>\n</ui>'}, "app.ui:2", "not-a-property"),
    ({"app.ui": '<ui><style>#label { background: linear-gradient(0deg, red, blue); }</style><label id="label"/></ui>'}, "app.ui:1", "header or status-bar"),
    ({"app.ui": '<ui><script src="controller.py"/></ui>', "controller.py": "def broken("}, "controller.py:1", "script failed"),
    ({"app.ui": '<ui><script src="controller.py"/>\n<button on-pressed="save"/>\n</ui>', "controller.py": 'from textui import action\n@action(target="missing")\ndef save(): pass'}, "app.ui:2", "missing"),
])
def test_check_reports_expected_errors_with_source_and_nonzero_status(tmp_path, capsys, files, source, diagnostic):
    entry = write_project(tmp_path, files)

    assert invoke("check", str(entry)) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert source in output.err and diagnostic in output.err
    assert "Traceback" not in output.err


def test_check_preserves_setup_failure_when_cleanup_also_fails(tmp_path, capsys):
    entry = write_project(tmp_path, {
        "app.ui": '<ui><script src="controller.py"/></ui>',
        "controller.py": '''
from pathlib import Path
def on_setup():
    raise ValueError("original setup failure")
def on_close():
    Path(__file__).with_suffix(".closed").write_text("closed once")
    raise ValueError("cleanup failure")
''',
    })

    assert invoke("check", str(entry)) == 1
    output = capsys.readouterr()
    assert "original setup failure" in output.err
    assert "cleanup failure" in output.err
    assert (tmp_path / "controller.closed").read_text() == "closed once"


def test_check_does_not_close_controllers_before_setup_begins(tmp_path, capsys):
    entry = write_project(tmp_path, {
        "app.ui": '<ui><script src="first.py"/><script src="second.py"/></ui>',
        "first.py": 'from pathlib import Path\ndef on_close(): Path(__file__).with_suffix(".closed").touch()',
        "second.py": 'raise ValueError("loading failed")',
    })

    assert invoke("check", str(entry)) == 1
    assert "loading failed" in capsys.readouterr().err
    assert not (tmp_path / "first.closed").exists()


@pytest.mark.parametrize("position", ["before", "after"])
def test_debug_keeps_expected_error_tracebacks(tmp_path, capsys, position):
    entry = tmp_path / "missing.ui"
    args = ["--debug", "check", str(entry)] if position == "before" else ["check", str(entry), "--debug"]

    assert invoke(*args) == 1
    assert "Traceback" in capsys.readouterr().err


def test_unexpected_failure_keeps_traceback_and_distinct_exit_status(monkeypatch, capsys):
    def broken(path):
        raise RuntimeError("unexpected implementation failure")
    monkeypatch.setattr(ProjectSource, "discover", broken)

    assert invoke("check", "app.ui") == 3
    output = capsys.readouterr()
    assert "Traceback" in output.err
    assert "unexpected implementation failure" in output.err


@pytest.mark.parametrize("example", ["project", "controls", "data", "components", "showcase"])
def test_check_accepts_shipped_projects_without_running_ready_hooks(example, capsys):
    entry = Path(__file__).parents[1] / "examples" / example / "app.ui"

    assert invoke("check", str(entry)) == 0
    assert capsys.readouterr().err == ""


def test_run_reports_missing_file_without_traceback(tmp_path, capsys):
    assert invoke("run", str(tmp_path / "missing.ui")) == 1
    assert "Traceback" not in capsys.readouterr().err


def test_run_reports_startup_style_failure_after_native_shutdown(tmp_path, monkeypatch, capsys):
    entry = write_project(tmp_path, {"app.ui": '<ui><label style="not-a-property: red;"/></ui>'})
    native_run = ProjectApp.run
    monkeypatch.setattr(ProjectApp, "run", lambda self: native_run(self, headless=True))

    assert invoke("run", str(entry)) == 1
    output = capsys.readouterr()
    assert "not-a-property" in output.err
    assert "app.ui:1" in output.err
    assert "Traceback" not in output.err


def test_run_preserves_explicit_application_exit_code(tmp_path, monkeypatch):
    entry = write_project(tmp_path, {
        "app.ui": '<ui><script src="controller.py"/></ui>',
        "controller.py": 'def on_ready(): window.app.exit(return_code=7)',
    })
    native_run = ProjectApp.run
    monkeypatch.setattr(ProjectApp, "run", lambda self: native_run(self, headless=True))

    assert invoke("run", str(entry)) == 7


def test_run_reports_unexpected_widget_mount_error_with_traceback(tmp_path, monkeypatch, capsys):
    entry = write_project(tmp_path, {
        "app.ui": '<ui><script src="controller.py"/><custom-label/></ui>',
        "controller.py": '''
from textui import ComponentSpec
from textual.widgets import Label
class Broken(Label):
    def on_mount(self):
        raise RuntimeError("unexpected widget failure")
def on_setup():
    window.registry.register(ComponentSpec(tag="custom-label", factory=lambda context: Broken()))
''',
    })
    native_run = ProjectApp.run
    monkeypatch.setattr(ProjectApp, "run", lambda self: native_run(self, headless=True))

    assert invoke("run", str(entry)) == 3
    output = capsys.readouterr()
    assert "unexpected widget failure" in output.err
    assert "Traceback" in output.err


@pytest.mark.skipif(sys.platform == "win32", reason="uses POSIX SIGINT delivery")
def test_run_sigint_returns_interruption_status_after_cleanup(tmp_path):
    entry = write_project(tmp_path, {
        "app.ui": '<ui><script src="controller.py"/></ui>',
        "controller.py": '''
from pathlib import Path
def on_ready(): Path(__file__).with_suffix(".ready").touch()
def on_close(): Path(__file__).with_suffix(".closed").touch()
''',
    })
    child = subprocess.Popen(
        [sys.executable, "-c", '''
import sys
from textui.__main__ import main
from textui.project_app import ProjectApp
native_run = ProjectApp.run
ProjectApp.run = lambda self: native_run(self, headless=True)
raise SystemExit(main(["run", sys.argv[1]]))
''', str(entry)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        deadline = time.monotonic() + 5
        while not (tmp_path / "controller.ready").exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert (tmp_path / "controller.ready").exists()
        child.send_signal(signal.SIGINT)
        output, error = child.communicate(timeout=5)
        assert child.returncode == 130, (output, error)
        assert "interrupted" in error
        assert (tmp_path / "controller.closed").exists()
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate()
