from textui import action


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


@action
def usage_selected(context) -> None:
    record = window.document.get_by_id("usage").get_record(context.event.row_key.value)
    window.document.get_by_id("feedback").update(
        f"{record['date']}: {record['requests']} requests"
    )


@action
def job_selected(context) -> None:
    window.document.get_by_id("feedback").update(
        f"Selected job: {context.event.row_key.value}"
    )


@action
def file_selected(context) -> None:
    window.document.get_by_id("feedback").update(
        f"Selected file: {context.event.node.data}"
    )


@action
def add_job() -> None:
    jobs = window.document.get_by_id("jobs")
    if not any(key.value == "deploy" for key in jobs.rows):
        jobs.add_row("Deploy", "Queued", key="deploy")
    files = window.document.get_by_id("files")
    if not any(node.data == "readme" for node in files.root.children):
        files.root.add_leaf("README.md", data="readme")
