from pathlib import Path

import pytest

from textui.__main__ import main
from textui.project_app import ProjectApp


def test_cli_runs_project_from_another_working_directory(tmp_path: Path, monkeypatch):
    project = tmp_path / "project"
    project.mkdir()
    entry = project / "app.ui"
    entry.write_text('<ui><label>Hello</label></ui>', encoding="utf-8")
    launched = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ProjectApp, "run", lambda self: launched.append(self.source.path))

    assert main(["run", str(entry)]) == 0
    assert launched == [entry]


def test_cli_requires_run_and_project_path(capsys):
    with pytest.raises(SystemExit) as caught:
        main([])
    assert caught.value.code == 2
    assert "run" in capsys.readouterr().err
