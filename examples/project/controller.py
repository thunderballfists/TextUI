from datetime import datetime

from textui import action, every


def on_ready() -> None:
    window.app.title = "TextUI Project"


@action
def greet() -> None:
    name = window.document.get_by_id("name").value.strip() or "friend"
    window.document.get_by_id("status").update(f"Hello, {name}!")


@action
def toggle_sidebar() -> None:
    sidebar = window.document.get_by_id("sidebar")
    sidebar.display = not sidebar.display


@action
def show_page(context) -> None:
    window.document.get_by_id("content").current = context.event.target


@every(1)
def show_time() -> None:
    window.document.get_by_id("clock").update(datetime.now().strftime("%H:%M:%S"))
