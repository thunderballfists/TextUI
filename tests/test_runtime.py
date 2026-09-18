import pytest
from textual.app import App
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Checkbox, Input, Label
import textui


def load(markup):
    return textui.DocumentLoader().from_string(markup, source_name="runtime.xml")


def custom_document(factory, markup='<ui><custom /></ui>'):
    registry = textui.ComponentRegistry()
    registry.register(textui.ComponentSpec('custom', factory))
    return textui.DocumentLoader(registry).from_string(markup, source_name='custom.xml')


@pytest.mark.asyncio
async def test_native_tree_multiple_roots_literal_content_and_common_attributes():
    assert hasattr(textui, 'TextUI'), 'The native runtime is missing'
    doc = load('''<ui><vertical id="box" class="one two one"><horizontal id="row">
    <label id="label">[bold]Literal[/bold]</label><button id="button" variant="primary">[x]</button>
    </horizontal><input id="input" password="false" max-length="5" placeholder="Name" />
    <checkbox id="flag" value="false" disabled="true">[x]</checkbox></vertical><label>Anonymous</label></ui>''')
    app = textui.TextUI(doc)
    with pytest.raises(textui.DocumentStateError):
        app.document.get_by_id('box')
    with pytest.raises(textui.ElementNotFoundError):
        app.document.get_by_id('absent')
    async with app.run_test():
        bound = app.document
        for name, cls in [('box', Vertical), ('row', Horizontal), ('label', Label), ('button', Button), ('input', Input), ('flag', Checkbox)]:
            assert isinstance(bound.get_by_id(name), cls)
        assert bound.get_by_id('flag').parent is bound.get_by_id('box')
        assert bound.get_by_id('box').classes == frozenset({'one', 'two'})
        assert bound.get_by_id('flag').value is False
        assert bound.get_by_id('flag').disabled is True
        assert bound.get_by_id('input').max_length == 5
        assert bound.get_by_id('label').content.plain == '[bold]Literal[/bold]'
        assert bound.get_by_id('button').label.plain == '[x]'
        assert bound.get_by_id('flag').label.plain == '[x]'
        assert list(app.screen.children)[-1].id is None
        with pytest.raises(textui.DocumentStateError):
            list(bound.compose())
        await bound.get_by_id('flag').remove()
        with pytest.raises(textui.DocumentStateError):
            bound.get_by_id('flag')


@pytest.mark.asyncio
async def test_document_reuse_creates_independent_widgets_and_app_binding_is_unique():
    doc = load('<ui><label id="label">Hi</label></ui>')
    first, second = textui.TextUI(doc), textui.TextUI(doc)
    with pytest.raises(textui.DocumentStateError):
        doc.bind(first, actions={})
    async with first.run_test():
        one = first.document.get_by_id('label')
    async with second.run_test():
        two = second.document.get_by_id('label')
        assert one is not two
    with pytest.raises(textui.DocumentStateError):
        first.document.get_by_id('label')


def test_binding_validates_all_actions_before_factories_or_styles():
    calls = []
    registry = textui.ComponentRegistry()
    registry.register(textui.ComponentSpec('custom', lambda context: calls.append(context), events={'pressed': textui.EventSpec(Button.Pressed, lambda event: event.button)}))
    doc = textui.DocumentLoader(registry).from_string('<ui><style>Label { color: red; }</style><custom on-pressed="save"/></ui>')
    app = App()
    before = app.stylesheet.source.copy()
    for actions in [{}, {'save': 5}, {'save': lambda ctx: None, 'unused': 5}]:
        with pytest.raises(textui.DocumentValidationError):
            doc.bind(app, actions=actions)
    assert calls == []
    assert app.stylesheet.source == before
    doc.bind(app, actions={'save': lambda ctx: None})


@pytest.mark.parametrize('factory', [lambda context: object(), lambda context: (_ for _ in ()).throw(ValueError('factory exploded'))])
def test_factory_errors_have_context_and_failed_binding_cannot_retry(factory):
    doc = custom_document(factory)
    app = App()
    bound = doc.bind(app, actions={})
    with pytest.raises(textui.ComponentBuildError) as error:
        list(bound.compose())
    assert error.value.location.source == 'custom.xml'
    assert error.value.location.tag == 'custom'
    assert error.value.__cause__ is not None
    with pytest.raises(textui.DocumentStateError):
        list(bound.compose())


def test_factory_cannot_reuse_widget_in_tree():
    widget = Label('shared')
    bound = custom_document(lambda context: widget, '<ui><custom/><custom/></ui>').bind(App(), actions={})
    with pytest.raises(textui.ComponentBuildError, match='fresh|reuse'):
        list(bound.compose())


@pytest.mark.asyncio
async def test_factory_cannot_return_mounted_widget():
    widget = Label('existing')
    class Host(App):
        def compose(self):
            yield widget
    app = Host()
    async with app.run_test():
        bound = custom_document(lambda context: widget).bind(App(), actions={})
        with pytest.raises(textui.ComponentBuildError, match='mount|parent|fresh'):
            list(bound.compose())


@pytest.mark.asyncio
async def test_binding_a_running_app_is_outside_supported_lifecycle():
    doc = load('<ui/>')
    app = App()
    async with app.run_test():
        with pytest.raises(textui.DocumentStateError, match='running|before'):
            doc.bind(app, actions={})


def test_factory_instance_cannot_be_recycled_across_unmounted_bindings():
    widget = Label('shared')
    doc = custom_document(lambda context: widget)
    first, second = doc.bind(App(), actions={}), doc.bind(App(), actions={})
    list(first.compose())
    with pytest.raises(textui.ComponentBuildError, match='fresh|reuse'):
        list(second.compose())


def test_empty_document_and_immutable_action_mapping():
    bound = load('<ui/>').bind(App(), actions={'unused': lambda ctx: None})
    with pytest.raises(TypeError):
        bound.actions['unused'] = lambda ctx: None
    assert list(bound.compose()) == []
    with pytest.raises(textui.DocumentStateError):
        bound.compose()
