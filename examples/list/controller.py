from textui import action


AGENTS = [
    {"id": "alpha", "name": "Alpha", "status": "Idle"},
    {"id": "bravo", "name": "Bravo", "status": "Working"},
    {"id": "charlie", "name": "Charlie", "status": "Offline"},
]


async def on_ready() -> None:
    await window.document.get_by_id("agents").set_items(AGENTS)


@action
def select_agent(context) -> None:
    agent = context.event.item
    window.document.get_by_id("agent-name").update(agent["name"])
    window.document.get_by_id("agent-status").update(agent["status"])
