"""Native clipboard round trip from an isolated wheel on disposable CI runners.

Run with ``python -I /checkout/tests/platform_smoke.py``. This writes synthetic
clipboard content and deliberately refuses to run outside GitHub Actions.
"""

import asyncio
import base64
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace


def require_disposable_runner() -> None:
    expected = {"darwin": "macOS", "win32": "Windows"}.get(sys.platform)
    if expected is None or os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_OS") != expected:
        raise RuntimeError("Native clipboard smoke requires a disposable macOS/Windows GitHub Actions runner")
    if not sys.flags.isolated:
        raise RuntimeError("Run the installed clipboard smoke with python -I")


def read_clipboard() -> str:
    if sys.platform == "darwin":
        environment = os.environ.copy()
        environment.pop("LC_ALL", None)
        environment["LC_CTYPE"] = "UTF-8"
        result = subprocess.run(
            ["pbpaste"], capture_output=True, check=True, timeout=5,
            env=environment,
        )
        return result.stdout.decode("utf-8")
    # Base64 ASCII avoids the runner's console code page corrupting Unicode.
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-STA", "-Command",
         "[Console]::Write([Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes([string](Get-Clipboard -Raw))))"],
        capture_output=True, check=True, timeout=10,
    )
    return base64.b64decode(result.stdout, validate=True).decode("utf-8")


async def main() -> None:
    require_disposable_runner()
    import textui

    origin = Path(textui.__file__).resolve()
    if not origin.is_relative_to(Path(sys.prefix).resolve()):
        raise RuntimeError(f"Expected installed wheel, found {origin}")
    payload = "TextUI clipboard smoke: café 🐍 漢字\nsecond line"
    terminal_messages = []
    app = SimpleNamespace(copy_to_clipboard=terminal_messages.append)
    backend = await textui.copy_to_clipboard(app, payload)
    expected = "pbcopy" if sys.platform == "darwin" else "clip"
    assert backend == expected, f"Native backend failed or was unavailable: {backend}"
    received = read_clipboard().replace("\r\n", "\n")
    assert received == payload, f"Native clipboard round trip differed: {received!r}"
    assert terminal_messages == [payload], "Terminal transport was not forwarded exactly once"
    print(f"Installed native clipboard smoke passed: {sys.platform}, {backend}, {origin}")


if __name__ == "__main__":
    asyncio.run(main())
