from textui import action


def _feedback(message: str) -> None:
    window.document.get_by_id("feedback").update(message)


@action
def status_changed(context) -> None:
    _feedback(f"Status: {context.event.value}")


@action
def enabled_changed(context) -> None:
    _feedback(f"Enabled: {str(context.event.value).lower()}")


@action
def notes_changed(context) -> None:
    _feedback(f"Notes: {len(context.event.text_area.text)} characters")


@action
def tab_changed(context) -> None:
    _feedback(f"Tab: {context.event.pane.id}")


@action
def priority_changed(context) -> None:
    _feedback(f"Priority: {context.event.pressed.id}")


@action
def details_collapsed() -> None:
    _feedback("Details collapsed")


@action
def details_expanded() -> None:
    _feedback("Details expanded")
