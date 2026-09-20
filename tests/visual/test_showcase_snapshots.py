"""Opt-in SVG regression coverage for the runnable showcase."""

from pathlib import Path
import re
import sys

import pytest

from textui import ProjectApp, ProjectSource


ENTRY = Path(__file__).resolve().parents[2] / "examples" / "showcase" / "app.ui"
SNAPSHOTS = Path(__file__).parent / "__snapshots__"


def canonicalize_svg(svg: str) -> str:
    return re.sub(r"terminal-\d+", "terminal-ID", svg)


def snapshot_path(name: str, platform: str) -> Path:
    return SNAPSHOTS / platform / f"{name}.svg"


def test_canonicalize_svg_ignores_generated_terminal_ids_only():
    first = '<g id="terminal-123-r1" fill="red" x="4">First</g>'
    second = '<g id="terminal-987-r1" fill="red" x="4">First</g>'

    assert canonicalize_svg(first) == canonicalize_svg(second)
    assert canonicalize_svg(first) != canonicalize_svg(second.replace("First", "Second"))
    assert canonicalize_svg(first) != canonicalize_svg(second.replace('x="4"', 'x="5"'))
    assert canonicalize_svg(first) != canonicalize_svg(second.replace('fill="red"', 'fill="blue"'))


def test_snapshot_path_is_platform_specific():
    assert snapshot_path("showcase-shell-80x24", "linux") == (
        SNAPSHOTS / "linux" / "showcase-shell-80x24.svg"
    )


async def freeze_snapshot(pilot):
    app = pilot.app
    app.window.timers.close()
    app.title = "TextUI showcase"
    app.theme = "textual-dark"
    app.document.get_by_id("clock").update("12:34:56")
    await pilot.pause(0.25)


async def open_help_modal(pilot):
    await freeze_snapshot(pilot)
    navigation = pilot.app.document.get_by_id("navigation")
    assert await pilot.click(navigation.items[3])
    await pilot.pause()
    opener = pilot.app.document.get_by_id("open-modal")
    opener.scroll_visible(animate=False)
    await pilot.pause()
    assert await pilot.click(opener, offset=(opener.region.width // 2, opener.region.height // 2))
    await pilot.pause(0.25)
    close = pilot.app.document.get_by_id("close-modal")
    x = close.region.x + close.region.width // 2
    y = close.region.y + close.region.height // 2
    assert pilot.app.get_widget_at(x, y)[0] is close


async def reopen_help_modal(pilot):
    await open_help_modal(pilot)
    close = pilot.app.document.get_by_id("close-modal")
    assert await pilot.click(close, offset=(close.region.width // 2, close.region.height // 2))
    await pilot.pause(0.25)
    opener = pilot.app.document.get_by_id("open-modal")
    assert await pilot.click(opener, offset=(opener.region.width // 2, opener.region.height // 2))
    await pilot.pause(0.25)
    close = pilot.app.document.get_by_id("close-modal")
    x = close.region.x + close.region.width // 2
    y = close.region.y + close.region.height // 2
    assert pilot.app.get_widget_at(x, y)[0] is close


async def assert_snapshot(name, size, prepare, request):
    app = ProjectApp(ProjectSource.discover(ENTRY))
    async with app.run_test(size=size) as pilot:
        await prepare(pilot)
        svg = app.export_screenshot(title="TextUI showcase", simplify=True)
    path = snapshot_path(name, sys.platform)
    if request.config.getoption("--snapshot-update"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(svg, encoding="utf-8")
    assert path.exists(), f"Missing baseline {path}; rerun with --snapshot-update after visual review."
    assert canonicalize_svg(svg) == canonicalize_svg(path.read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_showcase_shell_120x50_snapshot(request):
    await assert_snapshot("showcase-shell-120x50", (120, 50), freeze_snapshot, request)


@pytest.mark.asyncio
async def test_showcase_shell_80x24_snapshot(request):
    await assert_snapshot("showcase-shell-80x24", (80, 24), freeze_snapshot, request)


@pytest.mark.asyncio
async def test_showcase_first_modal_80x24_snapshot(request):
    await assert_snapshot("showcase-first-modal-80x24", (80, 24), open_help_modal, request)


@pytest.mark.asyncio
async def test_showcase_reopened_modal_80x24_snapshot(request):
    await assert_snapshot("showcase-reopened-modal-80x24", (80, 24), reopen_help_modal, request)
