import pytest
from textual import on
from textual.app import App
from textual.widgets import Button, Checkbox, Input
import textui


@pytest.mark.asyncio
async def test_pilot_forwards_native_messages_once_sync_async_and_initialization():
    seen = []
    def sync(context):
        seen.append(context)
    async def asynchronous(context):
        seen.append(context)
    actions = {'press': sync, 'change': asynchronous, 'submit': sync}
    doc = textui.DocumentLoader().from_string('''<ui><button id="button" on-pressed="press">Go</button>
    <input id="input" value="start" on-changed="change" on-submitted="submit"/>
    <checkbox id="checkbox" value="true" on-changed="change">Flag</checkbox></ui>''')
    app = textui.TextUI(doc, actions=actions)
    actions['press'] = lambda ctx: pytest.fail('mapping was not copied')
    async with app.run_test() as pilot:
        assert any(type(ctx.event) is Input.Changed and ctx.event.value == 'start' for ctx in seen)
        seen.clear()
        await pilot.click('#button')
        assert len(seen) == 1
        assert type(seen[0].event) is Button.Pressed
        await pilot.click('#input')
        await pilot.press('end', 'x', 'enter')
        await pilot.click('#checkbox')
        assert [type(ctx.event) for ctx in seen] == [Button.Pressed, Input.Changed, Input.Submitted, Checkbox.Changed]
        for ctx in seen:
            assert isinstance(ctx, textui.ActionContext)
            assert ctx.app is app and ctx.document is app.document
            assert ctx.widget is ctx.event.control
        assert app.document.get_by_id('input').value == 'startx'
        assert app.document.get_by_id('checkbox').value is False


@pytest.mark.asyncio
async def test_dispatch_identity_exact_type_no_binding_and_no_stop_or_prevent():
    seen = []
    app = textui.TextUI(textui.DocumentLoader().from_string('<ui><button id="bound" on-pressed="go">Go</button><button id="unbound">Other</button></ui>'), actions={'go': seen.append})
    class DerivedPressed(Button.Pressed):
        pass
    async with app.run_test():
        button = app.document.get_by_id('bound')
        assert await app.document.dispatch(Button.Pressed(Button('outside'))) is False
        assert await app.document.dispatch(Button.Pressed(app.document.get_by_id('unbound'))) is False
        assert await app.document.dispatch(DerivedPressed(button)) is False
        event = Button.Pressed(button)
        assert await app.document.dispatch(event) is True
        assert len(seen) == 1
        assert not event._stop_propagation
        assert not event._no_default_action


@pytest.mark.asyncio
@pytest.mark.parametrize('async_callback', [False, True])
async def test_callback_error_propagates_with_original_cause(async_callback):
    original = ValueError('action exploded')
    def sync(ctx):
        raise original
    async def asynchronous(ctx):
        raise original
    doc = textui.DocumentLoader().from_string('<ui><button id="button" on-pressed="explode"/></ui>', source_name='actions.xml')
    app = textui.TextUI(doc, actions={'explode': asynchronous if async_callback else sync})
    async with app.run_test():
        with pytest.raises(textui.ActionExecutionError) as error:
            await app.document.dispatch(Button.Pressed(app.document.get_by_id('button')))
        assert error.value.__cause__ is original
        assert error.value.location.source == 'actions.xml'
        assert 'explode' in str(error.value)


@pytest.mark.asyncio
async def test_existing_host_explicit_forwarding_and_native_handler_both_run():
    seen, native = [], []
    doc = textui.DocumentLoader().from_string('<ui><button id="button" on-pressed="go">Go</button></ui>')
    class Host(App):
        def __init__(self):
            super().__init__()
            self.document = doc.bind(self, actions={'go': seen.append})
        def compose(self):
            yield from self.document.compose()
        @on(Button.Pressed)
        async def forward(self, event):
            await self.document.dispatch(event)
        def on_button_pressed(self, event):
            native.append(event)
    app = Host()
    async with app.run_test() as pilot:
        await pilot.click('#button')
        assert len(seen) == len(native) == 1


@pytest.mark.asyncio
async def test_convenience_host_propagates_callback_failure_through_native_error_path():
    def fail(context):
        raise RuntimeError('native host failure')
    doc = textui.DocumentLoader().from_string('<ui><button id="button" on-pressed="fail">Fail</button></ui>')
    app = textui.TextUI(doc, actions={'fail': fail})
    with pytest.raises(textui.ActionExecutionError) as error:
        async with app.run_test() as pilot:
            await pilot.click('#button')
    assert isinstance(error.value.__cause__, RuntimeError)
