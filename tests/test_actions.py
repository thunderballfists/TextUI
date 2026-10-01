import asyncio

import pytest
from textual import on
from textual.app import App
from textual.widgets import Button, Checkbox, Input
import textui
from textui.actions import ActionOptions


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
@pytest.mark.parametrize("async_callback", [False, True])
async def test_immediate_callback_error_propagates_with_original_cause(async_callback):
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
async def test_delayed_callback_error_propagates_through_native_error_path():
    async def fail_after_await(context):
        await asyncio.sleep(0.01)
        raise ValueError("action exploded after await")

    doc = textui.DocumentLoader().from_string('<ui><button id="button" on-pressed="explode">Explode</button></ui>', source_name="actions.xml")
    app = textui.TextUI(doc, actions={"explode": fail_after_await})
    with pytest.raises(textui.ActionExecutionError) as error:
        async with app.run_test() as pilot:
            assert await pilot.click("#button")
            await pilot.pause()
    assert isinstance(error.value.__cause__, ValueError)
    assert error.value.location.source == "actions.xml"


@pytest.mark.asyncio
async def test_target_action_sets_loading_then_error_state():
    async def fail(context):
        assert context.target.id == "status"
        assert context.cancelled is False
        await asyncio.sleep(0)
        raise ValueError("refresh failed")

    doc = textui.DocumentLoader().from_string('<ui><button id="button" on-pressed="refresh">Refresh</button><label id="status">Ready</label></ui>')

    class Host(App):
        def __init__(self):
            super().__init__()
            self.document = doc.bind(self, actions={"refresh": fail}, action_metadata={"refresh": ActionOptions("status")})

        def compose(self):
            yield from self.document.compose()

    app = Host()
    with pytest.raises(textui.ActionExecutionError):
        async with app.run_test() as pilot:
            status = app.document.get_by_id("status")
            assert await app.document.dispatch(Button.Pressed(app.document.get_by_id("button")))
            assert status.has_class("-loading")
            await pilot.pause()
    assert not status.has_class("-loading")
    assert status.has_class("-error")
    assert status.textui_error == "refresh failed"


@pytest.mark.asyncio
async def test_superseding_target_action_cancels_prior_task_without_clearing_loading():
    started = asyncio.Event()
    cancelled = asyncio.Event()
    release = asyncio.Event()

    async def refresh(context):
        started.set()
        try:
            await release.wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    doc = textui.DocumentLoader().from_string('<ui><button id="button" on-pressed="refresh">Refresh</button><label id="status">Ready</label></ui>')

    class Host(App):
        def __init__(self):
            super().__init__()
            self.document = doc.bind(self, actions={"refresh": refresh}, action_metadata={"refresh": ActionOptions("status", True)})

        def compose(self):
            yield from self.document.compose()

    app = Host()
    async with app.run_test() as pilot:
        button = app.document.get_by_id("button")
        status = app.document.get_by_id("status")
        await app.document.dispatch(Button.Pressed(button))
        await started.wait()
        await app.document.dispatch(Button.Pressed(button))
        await cancelled.wait()
        assert status.has_class("-loading")
        release.set()
        await pilot.pause()
        assert not status.has_class("-loading")


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


class _LifecycleHost(App):
    def __init__(self, markup, actions, metadata):
        super().__init__()
        definition = textui.DocumentLoader().from_string(markup, source_name="lifecycle.xml")
        self.document = definition.bind(self, actions=actions, action_metadata=metadata)
        self.errors = []

    def compose(self):
        yield from self.document.compose()

    def _handle_exception(self, error):
        self.errors.append(error)

    def on_unmount(self):
        self.document.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("fails", [False, True])
async def test_sync_target_action_finishes_state_and_preserves_error_source(fails):
    original = ValueError("refresh failed")

    def refresh(context):
        assert context.target.has_class("-loading")
        if fails:
            raise original

    app = _LifecycleHost(
        '<ui><button id="button" on-pressed="refresh"/><label id="status"/></ui>',
        {"refresh": refresh}, {"refresh": ActionOptions("status")},
    )
    async with app.run_test():
        status = app.document.get_by_id("status")
        event = Button.Pressed(app.document.get_by_id("button"))
        if fails:
            with pytest.raises(textui.ActionExecutionError) as caught:
                await app.document.dispatch(event)
            assert caught.value.__cause__ is original
            assert caught.value.location.source == "lifecycle.xml"
            assert status.has_class("-error")
            assert status.textui_error == "refresh failed"
        else:
            status.add_class("-error")
            status.textui_error = "previous error"
            assert await app.document.dispatch(event)
            assert not status.has_class("-error")
            assert status.textui_error is None
        assert not status.has_class("-loading")


@pytest.mark.asyncio
@pytest.mark.parametrize("first_to_finish", [0, 1])
async def test_different_actions_keep_shared_target_loading_until_both_finish(first_to_finish):
    releases = [asyncio.Event(), asyncio.Event()]
    started = [asyncio.Event(), asyncio.Event()]

    async def first(context):
        started[0].set()
        await releases[0].wait()

    async def second(context):
        started[1].set()
        await releases[1].wait()

    app = _LifecycleHost('''<ui><button id="first" on-pressed="first"/>
        <button id="second" on-pressed="second"/><button id="sync" on-pressed="sync"/>
        <label id="status"/></ui>''',
        {"first": first, "second": second, "sync": lambda context: None},
        {name: ActionOptions("status", True) for name in ("first", "second", "sync")},
    )
    async with app.run_test() as pilot:
        try:
            for name in ("first", "second"):
                await app.document.dispatch(Button.Pressed(app.document.get_by_id(name)))
            await asyncio.gather(*(event.wait() for event in started))
            status = app.document.get_by_id("status")
            await app.document.dispatch(Button.Pressed(app.document.get_by_id("sync")))
            assert status.has_class("-loading")
            releases[first_to_finish].set()
            await pilot.pause()
            assert status.has_class("-loading")
            releases[1 - first_to_finish].set()
            await pilot.pause()
            assert not status.has_class("-loading")
            assert not status.has_class("-error")
        finally:
            for release in releases:
                release.set()
            await pilot.pause()
    assert app.errors == []


@pytest.mark.asyncio
async def test_textui_shutdown_cancels_untargeted_actions_and_marks_context():
    started, release, cancelled, finished = (asyncio.Event() for _ in range(4))
    contexts, effects = [], []

    async def wait(context):
        contexts.append(context)
        started.set()
        try:
            await release.wait()
            effects.append("resumed")
        except asyncio.CancelledError:
            cancelled.set()
            raise
        finally:
            finished.set()

    app = textui.TextUI(textui.DocumentLoader().from_string(
        '<ui><button id="button" on-pressed="wait"/></ui>'), actions={"wait": wait})
    try:
        async with app.run_test():
            await app.document.dispatch(Button.Pressed(app.document.get_by_id("button")))
            await started.wait()
        assert cancelled.is_set()
        assert contexts[0].cancelled
        release.set()
        await asyncio.wait_for(finished.wait(), timeout=1)
        assert effects == []
    finally:
        release.set()
        await asyncio.wait_for(finished.wait(), timeout=1)


@pytest.mark.asyncio
async def test_textui_exit_ignores_queued_action_messages_immediately():
    calls = []
    app = textui.TextUI(textui.DocumentLoader().from_string(
        '<ui><button id="button" on-pressed="go"/></ui>'), actions={"go": calls.append})
    async with app.run_test():
        event = Button.Pressed(app.document.get_by_id("button"))
        app.exit()
        assert await app.document.dispatch(event) is False
        app.document.close()
        assert await app.document.dispatch(event) is False
    assert calls == []


@pytest.mark.asyncio
async def test_superseded_failure_reports_source_without_overwriting_new_target_state():
    calls = 0
    cancelled, old_release, new_release = (asyncio.Event() for _ in range(3))
    contexts = []
    original = ValueError("stale failure")

    async def refresh(context):
        nonlocal calls
        calls += 1
        contexts.append(context)
        if calls == 1:
            try:
                await old_release.wait()
            except asyncio.CancelledError:
                cancelled.set()
                await old_release.wait()
            raise original
        await new_release.wait()

    app = _LifecycleHost(
        '<ui><button id="button" on-pressed="refresh"/><label id="status"/></ui>',
        {"refresh": refresh}, {"refresh": ActionOptions("status", True)},
    )
    async with app.run_test() as pilot:
        try:
            button = app.document.get_by_id("button")
            await app.document.dispatch(Button.Pressed(button))
            await app.document.dispatch(Button.Pressed(button))
            await cancelled.wait()
            assert contexts[0].cancelled
            assert not contexts[1].cancelled
            new_release.set()
            await pilot.pause()
            old_release.set()
            await pilot.pause()
            status = app.document.get_by_id("status")
            assert not status.has_class("-loading")
            assert not status.has_class("-error")
            assert status.textui_error is None
            assert len(app.errors) == 1
            assert app.errors[0].__cause__ is original
            assert app.errors[0].location.source == "lifecycle.xml"
        finally:
            old_release.set()
            new_release.set()
            await pilot.pause()


@pytest.mark.asyncio
async def test_sync_replacement_supersedes_async_action_without_error_state():
    contexts = []
    cancelled, release = asyncio.Event(), asyncio.Event()

    async def pending(context):
        try:
            await release.wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    def refresh(context):
        contexts.append(context)
        return pending(context) if len(contexts) == 1 else None

    app = _LifecycleHost(
        '<ui><button id="button" on-pressed="refresh"/><label id="status"/></ui>',
        {"refresh": refresh}, {"refresh": ActionOptions("status", True)},
    )
    async with app.run_test() as pilot:
        try:
            button = app.document.get_by_id("button")
            await app.document.dispatch(Button.Pressed(button))
            await app.document.dispatch(Button.Pressed(button))
            await pilot.pause()
            assert cancelled.is_set()
            assert contexts[0].cancelled
            status = app.document.get_by_id("status")
            assert not status.has_class("-loading")
            assert not status.has_class("-error")
        finally:
            release.set()
            await pilot.pause()
    assert app.errors == []
