import pytest
from textual.app import App
from textual.color import Color
import textui


@pytest.mark.asyncio
async def test_native_cascade_host_blocks_specificity_important_and_inline(tmp_path):
    css_path = tmp_path / 'host.tcss'
    css_path.write_text('Label { color: red; }')
    doc = textui.DocumentLoader().from_string('''<ui>
    <style>Label { color: blue; width: 10; } #specific { color: yellow; } #important { color: red !important; }</style>
    <style>Label { color: green; width: 15; text-opacity: 50%; } #important { color: blue; }</style>
    <label id="normal">Normal</label><label id="specific">Specific</label>
    <label id="important">Important</label><label id="inline" style="color: purple; width: 22;">Inline</label>
    </ui>''')
    class Host(App):
        CSS = 'Label { color: orange; width: 5; }'
        CSS_PATH = css_path
        def __init__(self):
            super().__init__()
            self.document = doc.bind(self, actions={})
        def compose(self):
            yield from self.document.compose()
    app = Host()
    async with app.run_test():
        get = app.document.get_by_id
        assert get('normal').styles.color == Color.parse('green')
        assert get('normal').styles.width.value == 15
        assert get('normal').styles.text_opacity == .5
        assert get('specific').styles.color == Color.parse('yellow')
        assert get('important').styles.color == Color.parse('red')
        assert get('inline').styles.color == Color.parse('purple')
        assert get('inline').styles.width.value == 22
        installed = app.stylesheet.source.copy()
        with pytest.raises(textui.DocumentStateError):
            list(app.document.compose())
        assert app.stylesheet.source == installed


@pytest.mark.asyncio
async def test_theme_variables_and_block_local_variables_use_native_context():
    doc = textui.DocumentLoader().from_string('<ui><style>$gap: 2; Label { padding: $gap; color: $primary; }</style><label id="label">Hello</label></ui>')
    app = textui.TextUI(doc)
    async with app.run_test():
        assert app.document.get_by_id('label').styles.padding.top == 2
        assert app.document.get_by_id('label').styles.color == Color.parse(app.get_css_variables()['primary'])


@pytest.mark.parametrize('markup, phrase', [
    ('<ui><style>Label { color: red; }</style><style>Label { imaginary: 5; }</style><label/></ui>', 'imaginary'),
    ('<ui><style>Label { color: ; }</style><label/></ui>', 'color'),
    ('<ui><style>Label { color: red; }</style><label style="color: $text;"/></ui>', 'variable'),
    ('<ui><style>Label { color: red; }</style><label style="imaginary: 5;"/></ui>', 'imaginary'),
    ('<ui><style>$gap: 2; Label { padding: $gap; }</style><style>Label { margin: $gap; }</style><label/></ui>', 'gap'),
])
def test_style_failure_is_source_aware_and_installs_nothing(markup, phrase):
    doc = textui.DocumentLoader().from_string(markup, source_name='styles.xml')
    app = App()
    original = app.stylesheet
    before = original.source.copy()
    bound = doc.bind(app, actions={})
    with pytest.raises(textui.DocumentStyleError) as error:
        list(bound.compose())
    assert error.value.location.source == 'styles.xml'
    assert error.value.location.line == 1
    assert phrase in str(error.value).lower()
    assert error.value.__cause__ is not None
    assert app.stylesheet is original
    assert app.stylesheet.source == before


def test_construction_failure_does_not_install_valid_styles():
    registry = textui.ComponentRegistry()
    registry.register(textui.ComponentSpec('broken', lambda ctx: object()))
    doc = textui.DocumentLoader(registry).from_string('<ui><style>Label { color: red; }</style><broken/></ui>')
    app = App()
    before = app.stylesheet.source.copy()
    with pytest.raises(textui.ComponentBuildError):
        list(doc.bind(app, actions={}).compose())
    assert app.stylesheet.source == before


def test_css_error_preserves_relative_line_and_original_document_line():
    doc = textui.DocumentLoader().from_string('<ui>\n<style>\nLabel {\n nonsense: 1;\n}\n</style></ui>', source_name='bad.xml')
    with pytest.raises(textui.DocumentStyleError) as error:
        list(doc.bind(App(), actions={}).compose())
    assert error.value.location.line == 4
    assert error.value.__cause__ is not None


def test_invalid_variable_value_points_to_use_in_original_document():
    doc = textui.DocumentLoader().from_string('<ui>\n<style>$bad: 99;\nLabel {\n color: $bad;\n}\n</style></ui>', source_name='variables.xml')
    with pytest.raises(textui.DocumentStyleError) as error:
        list(doc.bind(App(), actions={}).compose())
    assert error.value.location.line == 4
    assert 'CSS line 3' in str(error.value)
