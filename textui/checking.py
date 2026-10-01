"""Project preparation checks without a terminal or mounted message pumps."""
from __future__ import annotations

from .project import ProjectSource
from .project_app import ProjectApp


async def check_project(source: ProjectSource) -> None:
    """Execute trusted setup and construction, then close without becoming ready."""
    app = ProjectApp(source)
    with app._context():
        try:
            await app.on_load()
            app.document._check_unmounted()
        except BaseException as error:
            if app._setup_completed:
                await app._close_after_error(error)
            raise
        else:
            await app._close_once()
