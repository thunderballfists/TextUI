import os


collect_ignore_glob = [] if os.environ.get("TEXTUI_VISUAL_TESTS") == "1" else ["test_*.py"]


def pytest_addoption(parser):
    parser.addoption(
        "--snapshot-update",
        action="store_true",
        default=False,
        help="replace approved TextUI SVG visual baselines",
    )


import pytest


@pytest.fixture(autouse=True)
def snapshot_color_environment(monkeypatch):
    # Screenshots verify the chosen theme, independent of the invoking shell.
    monkeypatch.delenv("NO_COLOR", raising=False)
