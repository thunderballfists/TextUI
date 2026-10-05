"""Small command-line entry point for local TextUI projects."""
from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
import sys
import traceback
from typing import Any

from .checking import check_project
from .errors import TextUIError
from .project import ProjectSource
from .project_app import ProjectApp
from .static_check import check_static, diagnostic


class _CLIProjectApp(ProjectApp):
    """Retain native shutdown, reporting failures after terminal restoration."""

    cli_error: Exception | None = None

    async def run_async(self, **options: Any) -> Any:
        result = await super().run_async(**options)
        task = asyncio.current_task()
        # Textual may consume runner cancellation while shutting down its loop.
        # Re-propagate it after native cleanup so asyncio can report SIGINT.
        if task is not None and task.cancelling():
            raise asyncio.CancelledError
        return result

    def _handle_exception(self, error: Exception) -> None:
        if self.cli_error is None:
            self.cli_error = error
        elif error is not self.cli_error:
            self.cli_error.add_note(f"Shutdown also failed: {error}")
        self.exit(return_code=1)
        self.panic()


def _report_error(error: Exception, *, debug: bool) -> int:
    if debug or not isinstance(error, TextUIError):
        traceback.print_exception(error, file=sys.stderr)
    else:
        print(f"textui: {error}", file=sys.stderr)
        for note in getattr(error, "__notes__", ()):
            print(note, file=sys.stderr)
    return 1 if isinstance(error, TextUIError) else 3


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="textui")
    parser.set_defaults(debug=False)
    parser.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help="show tracebacks for project errors")
    commands = parser.add_subparsers(dest="command", required=True)
    spec_command = commands.add_parser("spec", help="generate registry-derived authoring references and editor data")
    spec_command.add_argument("--output", default=".", help="output directory (default: current directory)")
    spec_command.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help="show tracebacks")
    for name, help_text in (("run", "run a local .ui project"), ("check", "check a trusted project without mounting; runs linked scripts, on_setup and on_close")):
        command = commands.add_parser(name, help=help_text, description=help_text)
        command.add_argument("path", help="entry .ui file")
        command.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help="show tracebacks for project errors")
        if name == "check":
            command.add_argument("--static", action="store_true", help="check built-in markup without executing linked Python or constructing widgets")
            command.add_argument("--format", choices=("text", "json"), default="text", help="static-check diagnostic format")
    arguments = parser.parse_args(argv)
    if arguments.command == "check" and arguments.format == "json" and not arguments.static:
        parser.error("--format json requires check --static")
    try:
        if arguments.command == "spec":
            from .authoring import write_spec

            written = write_spec(arguments.output)
            print(f"Generated {len(written)} authoring artifacts in {arguments.output}")
            return 0
        if arguments.command == "check" and arguments.static:
            try:
                check_static(arguments.path)
            except TextUIError as error:
                if arguments.format == "json":
                    print(json.dumps([diagnostic(error, arguments.path)], ensure_ascii=False))
                    return 1
                raise
            print("[]" if arguments.format == "json" else f"Checked {arguments.path} (static)")
            return 0
        source = ProjectSource.discover(arguments.path)
        if arguments.command == "check":
            asyncio.run(check_project(source))
            print(f"Checked {source.path}")
            return 0
        app = _CLIProjectApp(source)
        app.run()
        if app.cli_error is not None:
            return _report_error(app.cli_error, debug=arguments.debug)
        return app.return_code or 0
    except Exception as error:
        return _report_error(error, debug=arguments.debug)
    except KeyboardInterrupt:
        print("textui: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
