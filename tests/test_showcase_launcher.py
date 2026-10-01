"""Run the checkout launcher with only the external installer replaced."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

def run_launcher(tmp_path, *, install_exit=0, run_exit=0, missing_uvx=False):
    source = Path(__file__).parents[1] / "showcase"
    assert source.is_file(), "The checkout needs a showcase launcher"
    checkout = tmp_path / "checkout with spaces"
    checkout.mkdir()
    launcher = checkout / "showcase"
    shutil.copy2(source, launcher)
    caller = tmp_path / "another directory"
    caller.mkdir()
    tools = tmp_path / "tools"
    tools.mkdir()
    calls = tmp_path / "calls.jsonl"
    fake = tools / "uvx"
    fake.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "with open(os.environ['LAUNCH_CALLS'], 'a') as output:\n"
        "    output.write(json.dumps({'args': sys.argv[1:], 'cwd': os.getcwd(), "
        "'active_env': os.environ.get('VIRTUAL_ENV'), "
        "'conda_env': os.environ.get('CONDA_PREFIX'), "
        "'create': os.environ.get('POETRY_VIRTUALENVS_CREATE'), "
        "'in_project': os.environ.get('POETRY_VIRTUALENVS_IN_PROJECT'), "
        "'poetry_python': os.environ.get('POETRY_VIRTUALENVS_USE_POETRY_PYTHON')}) + '\\n')\n"
        "sys.exit(int(os.environ['INSTALL_EXIT' if 'install' in sys.argv else 'RUN_EXIT']))\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    environment = {
        **os.environ,
        "PATH": "" if missing_uvx else f"{tools}{os.pathsep}/usr/bin{os.pathsep}/bin",
        "LAUNCH_CALLS": str(calls),
        "INSTALL_EXIT": str(install_exit),
        "RUN_EXIT": str(run_exit),
        "VIRTUAL_ENV": str(tmp_path / "unrelated environment"),
        "CONDA_PREFIX": str(tmp_path / "unrelated conda"),
        "POETRY_VIRTUALENVS_CREATE": "false",
        "POETRY_VIRTUALENVS_IN_PROJECT": "true",
        "POETRY_VIRTUALENVS_USE_POETRY_PYTHON": "false",
    }
    result = subprocess.run(
        [str(launcher)], cwd=caller, env=environment, capture_output=True, text=True,
    )
    recorded = [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []
    return result, recorded, checkout


def test_launcher_installs_then_runs_showcase_from_another_directory(tmp_path):
    result, calls, checkout = run_launcher(tmp_path)

    assert result.returncode == 0, result.stderr
    prefix = ["--python", "3.12", "--from", "poetry==2.4.3", "poetry"]
    assert [call["args"] for call in calls] == [
        prefix + ["install", "--with", "test", "--no-interaction"],
        prefix + ["run", "python", "-m", "textui", "run", str(checkout / "examples/showcase/app.ui")],
    ]
    assert all(call["cwd"] == str(checkout) for call in calls)
    assert all(call["active_env"] is None and call["conda_env"] is None for call in calls)
    assert all(call["create"] == "true" and call["in_project"] == "false" for call in calls)
    assert all(call["poetry_python"] == "true" for call in calls)


def test_launcher_does_not_run_after_installation_fails(tmp_path):
    result, calls, _ = run_launcher(tmp_path, install_exit=17)

    assert result.returncode == 17
    assert len(calls) == 1


def test_launcher_preserves_application_exit_status(tmp_path):
    result, calls, _ = run_launcher(tmp_path, run_exit=23)

    assert result.returncode == 23
    assert len(calls) == 2


def test_launcher_explains_missing_uvx_without_attempting_setup(tmp_path):
    result, calls, _ = run_launcher(tmp_path, missing_uvx=True)

    assert result.returncode == 127
    assert "uv" in result.stderr and "https://docs.astral.sh/uv/" in result.stderr
    assert not calls
