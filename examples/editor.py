"""Run with ``python -m examples.editor`` from the repository root."""

from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.content import Content
from textual.widgets import Button, Checkbox, Input, Label

from textui import ActionContext, DocumentLoader


class Editor(App):
    """A normal Textual App hosting one document and an explicit Save action."""

    BINDINGS = [("ctrl+q", "quit", "Quit")]

    def __init__(self) -> None:
        super().__init__()
        definition = DocumentLoader().from_file(Path(__file__).with_name("form.xml"))
        self.document = definition.bind(self, actions={"save_document": self.save_document})

    def compose(self) -> ComposeResult:
        yield from self.document.compose()

    @on(Button.Pressed)
    @on(Input.Changed)
    @on(Input.Submitted)
    @on(Checkbox.Changed)
    async def forward_document_message(
        self, event: Button.Pressed | Input.Changed | Input.Submitted | Checkbox.Changed
    ) -> None:
        await self.document.dispatch(event)

    def save_document(self, context: ActionContext) -> None:
        name = context.document.get_by_id("name")
        status = context.document.get_by_id("status")
        assert isinstance(name, Input)
        assert isinstance(status, Label)
        status.update(Content(f"Saved {name.value}"))


if __name__ == "__main__":
    Editor().run()
