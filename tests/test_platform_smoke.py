"""Keep the opt-in native clipboard probe from writing during ordinary tests."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("actions,runner", [("", "macOS"), ("false", "Windows"), ("true", "Linux")])
def test_native_probe_refuses_nonmatching_runner_before_touching_clipboard(actions, runner):
    result = subprocess.run(
        [sys.executable, "-I", str(Path(__file__).with_name("platform_smoke.py"))],
        env={**os.environ, "GITHUB_ACTIONS": actions, "RUNNER_OS": runner},
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 1
    assert "requires a disposable macOS/Windows" in result.stderr


@pytest.mark.skipif(sys.platform not in ("darwin", "win32"), reason="native platforms only")
def test_native_probe_refuses_nonisolated_python_before_touching_clipboard():
    result = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("platform_smoke.py"))],
        env={**os.environ, "GITHUB_ACTIONS": "true", "RUNNER_OS": "macOS" if sys.platform == "darwin" else "Windows"},
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 1
    assert "with python -I" in result.stderr
