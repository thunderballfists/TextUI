import pytest
from textual import on
from textual.message import Message
from textual.widgets import Label
import textui


@pytest.mark.asyncio
async def test_typed_custom_component_and_explicit_custom_message_forwarding():
    class Status(Label):
        class Updated(Message):
            def __init__(self, source):
                self.source = source
                super().__init__()
        def signal(self):
            self.post_message(self.Updated(self))
    contexts = []
    def factory(context):
        assert context.attributes['count'] == 3
        assert type(context.attributes['count']) is int
        return Status(str(context.attributes['count']))
    registry = textui.ComponentRegistry()
    registry.register(textui.ComponentSpec('status', factory, attributes={'count': textui.AttributeSpec(textui.integer(minimum=0), required=True)}, events={'updated': textui.EventSpec(Status.Updated, lambda event: event.source)}))
    doc = textui.DocumentLoader(registry).from_string('<ui><status id="status" count="3" on-updated="record"/></ui>')
    class Host(textui.TextUI):
        @on(Status.Updated)
        async def forward_custom(self, event):
            await self.document.dispatch(event)
    app = Host(doc, actions={'record': contexts.append})
    async with app.run_test() as pilot:
        status = app.document.get_by_id('status')
        status.signal()
        await pilot.pause()
        assert len(contexts) == 1
        assert contexts[0].widget is status
        assert contexts[0].event.source is status
