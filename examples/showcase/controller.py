from datetime import datetime

from textui import action, every


AGENTS = [
    {"name": "Alpha", "status": "Ready"},
    {"name": "Bravo", "status": "Working"},
]


def _feedback(message: str) -> None:
    window.document.get_by_id("feedback").update(message)


async def on_ready() -> None:
    await window.document.get_by_id("agents").set_items(AGENTS)


@every(1)
def update_clock() -> None:
    window.document.get_by_id("clock").update(datetime.now().strftime("%H:%M:%S"))


@action
def toggle_sidebar() -> None:
    sidebar = window.document.get_by_id("sidebar")
    sidebar.display = not sidebar.display


@action
def quit_app() -> None:
    window.app.exit()


@action
def show_page(context) -> None:
    window.document.get_by_id("content").current = context.event.target


@action
def greet(context) -> None:
    _feedback(f"Hello, {context.event.input.value.strip() or 'friend'}!")


@action
def notify_changed(context) -> None: _feedback(f"Notifications: {context.event.value}")


@action
def status_changed(context) -> None: _feedback(f"Status: {context.event.value}")


@action
def enabled_changed(context) -> None: _feedback(f"Enabled: {context.event.value}")


@action
def notes_changed(context) -> None: _feedback(f"Notes: {len(context.event.text_area.text)} characters")


@action
def tab_changed(context) -> None: _feedback(f"Tab: {context.event.pane.id}")


@action
def priority_changed(context) -> None: _feedback(f"Priority: {context.event.pressed.id}")


@action
def details_expanded() -> None: _feedback("Details expanded")


@action
def details_collapsed() -> None: _feedback("Details collapsed")


@action
def refresh_usage() -> None:
    window.document.get_by_id("usage").set_rows([
        {
            "record_id": "2026-09-19-alpha",
            "date": "2026-09-19",
            "requests": 42,
            "cost_usd": 1.25,
        },
        {
            "record_id": "2026-09-19-bravo",
            "date": "2026-09-19",
            "requests": 17,
            "cost_usd": 0.48,
        },
    ])
    _feedback("Usage refreshed")


@action
def usage_selected(context) -> None:
    record = window.document.get_by_id("usage").get_record(context.event.row_key.value)
    _feedback(f"Usage: {record['requests']} requests")


@action
def job_selected(context) -> None: _feedback(f"Job: {context.event.row_key.value}")


@action
def file_selected(context) -> None: _feedback(f"File: {context.event.node.data}")


@action
def add_data() -> None:
    jobs = window.document.get_by_id("jobs")
    if not any(key.value == "deploy" for key in jobs.rows): jobs.add_row("Deploy", "Queued", key="deploy")
    files = window.document.get_by_id("files")
    if not any(node.data == "readme" for node in files.root.children): files.root.add_leaf("README.md", data="readme")
    _feedback("Added deploy and README.md")


@action
def select_agent(context) -> None:
    window.document.get_by_id("agent-detail").update(f"{context.event.item['name']}: {context.event.item['status']}")


@action
def select_alpha() -> None: _feedback("Alpha selected from a component slot")


@action
def append_log() -> None:
    window.document.get_by_id("transcript").append("A native log entry")
    _feedback("Log appended")


@action
async def open_modal(context) -> None:
    await context.push_modal("help")


@action
def close_modal(context) -> None:
    context.dismiss_modal("closed")
