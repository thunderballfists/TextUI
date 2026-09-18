"""Small command-line entry point for local TextUI projects."""
from __future__ import annotations

import argparse
from collections.abc import Sequence

from .project import ProjectSource
from .project_app import ProjectApp


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="textui")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="run a local .ui project")
    run.add_argument("path", help="entry .ui file")
    arguments = parser.parse_args(argv)
    ProjectApp(ProjectSource.discover(arguments.path)).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
