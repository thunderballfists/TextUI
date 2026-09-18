from textui import action


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
