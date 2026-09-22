import pytest
from textual.widgets import Button

from textui import ComponentRegistry, ComponentSpec, DocumentLoader, DocumentStateError, ElementNotFoundError, ProjectApp, ProjectSource, TextUI
from textual.widgets import Label


MODAL_MARKUP = '''<ui>
  <button id="open" on-pressed="open_modal">Open</button>
  <label id="result">Waiting</label>
  <modal id="pick" dismissable="true">
    <label>Choose an account</label>
    <button id="choose" on-pressed="choose">Choose Alpha</button>
  </modal>
</ui>'''


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [(120, 50), (80, 24)])
async def test_modal_reopens_with_visible_click_target_and_restores_focus(size):
    """A hidden or stale rebuilt modal must fail through its real button hit target."""
    results = []

    async def open_modal(context):
        results.append(await context.push_modal("pick"))

    def choose(context):
        context.dismiss_modal("alpha")

    app = TextUI(
        DocumentLoader().from_string(MODAL_MARKUP),
        actions={"open_modal": open_modal, "choose": choose},
    )
    async with app.run_test(size=size) as pilot:
        base_screen = app.screen
        screens = []
        choices = []
        for expected in ("alpha", None, "alpha"):
            opener = app.document.get_by_id("open")
            opener.focus()
            assert await pilot.click(opener)
            await pilot.pause()
            screen = app.screen
            choose_button = app.document.get_by_id("choose")
            panel = screen.query_one(".markup-modal-content")
            assert panel.region.width >= 28
            assert screen.region.contains_region(panel.region)
            assert choose_button.region.width > 0
            assert choose_button.region.height > 0
            assert screen.region.contains_region(choose_button.region)
            x = choose_button.region.x + choose_button.region.width // 2
            y = choose_button.region.y + choose_button.region.height // 2
            assert app.get_widget_at(x, y)[0] is choose_button
            if expected is None:
                await pilot.press("escape")
            else:
                assert await pilot.click(choose_button, offset=(choose_button.region.width // 2, 1))
            await pilot.pause()
            assert app.screen is base_screen
            assert app.focused is opener
            assert results[-1] == expected
            with pytest.raises(DocumentStateError):
                app.document.get_by_id("choose")
            screens.append(screen)
            choices.append(choose_button)
        assert results == ["alpha", None, "alpha"]
        assert len({id(screen) for screen in screens}) == 3
        assert len({id(button) for button in choices}) == 3


@pytest.mark.asyncio
async def test_nondismissable_modal_ignores_escape_and_reopens_after_click():
    """Escape must not discard a non-dismissable modal or prevent its next open."""
    markup = MODAL_MARKUP.replace('dismissable="true"', 'dismissable="false"')
    results = []

    async def open_modal(context):
        results.append(await context.push_modal("pick"))

    def choose(context):
        context.dismiss_modal("alpha")

    app = TextUI(DocumentLoader().from_string(markup), actions={"open_modal": open_modal, "choose": choose})
    async with app.run_test() as pilot:
        for _ in range(2):
            assert await pilot.click("#open")
            await pilot.pause()
            modal = app.screen
            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is modal
            assert await pilot.click("#choose")
            await pilot.pause()
        assert results == ["alpha", "alpha"]


def binding_count(document):
    return sum(len(entries) for entries in document._bindings.values())


@pytest.mark.asyncio
async def test_dismissal_releases_anonymous_modal_action_bindings():
    """Removing public IDs alone must not retain an anonymous modal callback."""
    markup = '''<ui>
      <button id="open" on-pressed="open_modal">Open</button>
      <modal id="pick"><button on-pressed="record">Choose</button></modal>
    </ui>'''
    records = []

    def open_modal(context):
        context.push_modal("pick")

    def record(context):
        records.append(context.widget)
        context.dismiss_modal("done")

    app = TextUI(DocumentLoader().from_string(markup), actions={"open_modal": open_modal, "record": record})
    async with app.run_test() as pilot:
        baseline = binding_count(app.document)
        assert await pilot.click("#open")
        await pilot.pause()
        old_button = app.screen.query_one(Button)
        assert await pilot.click(old_button)
        await pilot.pause()
        assert binding_count(app.document) == baseline
        assert await app.document.dispatch(Button.Pressed(old_button)) is False
        assert records == [old_button]


@pytest.mark.asyncio
async def test_modal_cannot_open_same_definition_twice_before_dismissal():
    """A duplicate modal definition would otherwise leave an ambiguous screen stack."""
    app = TextUI(DocumentLoader().from_string(MODAL_MARKUP), actions={"open_modal": lambda context: None, "choose": lambda context: None})
    async with app.run_test() as pilot:
        first = app.document.push_modal("pick")
        await pilot.pause()
        first_screen = app.screen
        with pytest.raises(DocumentStateError, match="already active"):
            app.document.push_modal("pick")
        assert app.screen is first_screen
        app.document.dismiss_modal("done")
        await pilot.pause()
        assert await first == "done"


@pytest.mark.asyncio
async def test_modal_can_reopen_immediately_after_its_result_resolves():
    """A completed modal future must not expose an old screen with the same ID."""
    app = TextUI(DocumentLoader().from_string(MODAL_MARKUP), actions={"open_modal": lambda context: None, "choose": lambda context: None})
    async with app.run_test() as pilot:
        first = app.document.push_modal("pick")
        await pilot.pause()
        app.document.dismiss_modal("first")
        assert await first == "first"
        second = app.document.push_modal("pick")
        await pilot.pause()
        app.document.dismiss_modal("second")
        assert await second == "second"


@pytest.mark.asyncio
async def test_modal_result_exposes_mount_completion_before_dismissal():
    app = TextUI(DocumentLoader().from_string(MODAL_MARKUP), actions={"open_modal": lambda context: None, "choose": lambda context: None})
    async with app.run_test() as pilot:
        result = app.document.push_modal("pick")
        await result.mounted
        account_button = app.document.get_by_id("choose")
        assert account_button.is_mounted
        assert not result.done()
        app.document.dismiss_modal("selected")
        await pilot.pause()
        assert await result == "selected"


@pytest.mark.asyncio
async def test_failed_modal_push_leaves_no_registered_modal_state(monkeypatch):
    """A synchronous screen-push failure must not poison the next real open."""
    app = TextUI(DocumentLoader().from_string(MODAL_MARKUP), actions={"open_modal": lambda context: None, "choose": lambda context: None})
    async with app.run_test() as pilot:
        before_widgets = dict(app.document._widgets)
        before_bindings = {message_type: list(entries) for message_type, entries in app.document._bindings.items()}
        original_push = app.push_screen

        def fail_push(screen, *, callback=None):
            raise RuntimeError("push failed")

        monkeypatch.setattr(app, "push_screen", fail_push)
        with pytest.raises(RuntimeError, match="push failed"):
            app.document.push_modal("pick")
        assert app.document._widgets == before_widgets
        assert app.document._bindings == before_bindings
        monkeypatch.setattr(app, "push_screen", original_push)
        result = app.document.push_modal("pick")
        await pilot.pause()
        app.document.dismiss_modal("done")
        await pilot.pause()
        assert await result == "done"


@pytest.mark.asyncio
async def test_nested_distinct_modals_preserve_first_modal_bindings():
    """Dismissing a nested modal must not remove the active parent modal's action."""
    markup = '''<ui>
      <modal id="first"><button id="open-second" on-pressed="open_second">Second</button><button id="close-first" on-pressed="close_first">Close</button></modal>
      <modal id="second"><button id="close-second" on-pressed="close_second">Close</button></modal>
    </ui>'''

    def open_second(context):
        context.push_modal("second")

    def close_first(context):
        context.dismiss_modal("first")

    def close_second(context):
        context.dismiss_modal("second")

    app = TextUI(DocumentLoader().from_string(markup), actions={"open_second": open_second, "close_first": close_first, "close_second": close_second})
    async with app.run_test() as pilot:
        first = app.document.push_modal("first")
        await pilot.pause()
        assert await pilot.click("#open-second")
        await pilot.pause()
        second = app.screen
        assert await pilot.click("#close-second")
        await pilot.pause()
        assert app.screen is not second
        assert await pilot.click("#close-first")
        await pilot.pause()
        assert await first == "first"


@pytest.mark.asyncio
async def test_cancelled_modal_future_still_releases_modal_bindings():
    """Cancelling a caller's result wait must not skip dismissal cleanup."""
    app = TextUI(DocumentLoader().from_string(MODAL_MARKUP), actions={"open_modal": lambda context: None, "choose": lambda context: None})
    async with app.run_test() as pilot:
        baseline = binding_count(app.document)
        result = app.document.push_modal("pick")
        await pilot.pause()
        result.cancel()
        app.document.dismiss_modal("ignored")
        await pilot.pause()
        assert result.cancelled()
        assert binding_count(app.document) == baseline


@pytest.mark.asyncio
async def test_dismissal_releases_modal_compact_controls():
    markup = MODAL_MARKUP.replace("<ui>", '<ui><style preset="compact"/>')
    app = TextUI(DocumentLoader().from_string(markup), actions={"open_modal": lambda context: None, "choose": lambda context: None})
    async with app.run_test() as pilot:
        baseline = len(app.document._compact_widgets)
        result = app.document.push_modal("pick")
        await pilot.pause()
        assert len(app.document._compact_widgets) == baseline + 1
        app.document.dismiss_modal("done")
        assert await result == "done"
        assert len(app.document._compact_widgets) == baseline


@pytest.mark.asyncio
async def test_app_shutdown_resolves_open_modal_and_releases_its_state():
    """Shutdown must not strand modal callers or leave a modal marked active."""
    app = TextUI(DocumentLoader().from_string(MODAL_MARKUP), actions={"open_modal": lambda context: None, "choose": lambda context: None})
    async with app.run_test() as pilot:
        baseline = binding_count(app.document)
        result = app.document.push_modal("pick")
        await pilot.pause()
        app.exit()
    assert result.done()
    assert result.result() is None
    assert "pick" not in app.document._active_modal_ids
    assert binding_count(app.document) == baseline


@pytest.mark.asyncio
async def test_private_component_modal_button_binding_is_released(tmp_path):
    """Component-private IDs are not public, but their modal actions still expire."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "choice.ui").write_text(
        '<component><button id="choice" on-pressed="close_modal">Choose</button></component>',
        encoding="utf-8",
    )
    (tmp_path / "app.ui").write_text(
        '<ui><component src="components/choice.ui" as="choice"/><button id="open" on-pressed="open_modal">Open</button><modal id="pick"><choice/></modal></ui>',
        encoding="utf-8",
    )

    def open_modal(context):
        context.push_modal("pick")

    def close_modal(context):
        context.dismiss_modal("done")

    app = ProjectApp(ProjectSource.discover(tmp_path / "app.ui"), actions={"open_modal": open_modal, "close_modal": close_modal})
    async with app.run_test() as pilot:
        baseline = binding_count(app.document)
        assert await pilot.click("#open")
        await pilot.pause()
        private_button = app.screen.query_one(Button)
        with pytest.raises(ElementNotFoundError):
            app.document.get_by_id(private_button.id)
        assert await pilot.click(private_button)
        await pilot.pause()
        assert binding_count(app.document) == baseline


@pytest.mark.asyncio
async def test_custom_component_named_modal_composes_as_an_ordinary_widget():
    """Only the built-in modal factory receives deferred-screen treatment."""
    registry = ComponentRegistry()
    registry.register(ComponentSpec("modal", lambda context: Label(context.text or "ordinary"), text_policy="text"))
    app = TextUI(DocumentLoader(registry).from_string('<ui><modal id="ordinary">Ordinary</modal></ui>'))
    async with app.run_test():
        ordinary = app.document.get_by_id("ordinary")
        assert isinstance(ordinary, Label)
        assert str(ordinary.render()) == "Ordinary"
