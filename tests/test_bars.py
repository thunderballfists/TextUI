import pytest
from textual.renderables.gradient import LinearGradient

from textui import DocumentLoader, DocumentValidationError, TextUI


MARKUP = '''<ui>
  <header id="top">
    <left><label id="brand">TextUI</label></left>
    <center><label id="identity">Abe</label></center>
    <right><label id="context">Production</label></right>
  </header>
</ui>'''


def test_header_and_status_bar_lower_as_slot_containers():
    document = DocumentLoader().from_string(MARKUP)
    header = document.nodes[0]
    assert header.spec.tag == "header"
    assert [slot.spec.tag for slot in header.children] == ["left", "center", "right"]
    assert DocumentLoader().from_string('<ui><status-bar><right><label>Ready</label></right></status-bar></ui>')


@pytest.mark.parametrize("markup", [
    '<ui><left><label>Orphaned</label></left></ui>',
    '<ui><header><left/><left/></header></ui>',
    '<ui><header><label>Unslotted</label></header></ui>',
])
def test_slots_must_belong_to_one_header_or_status_bar(markup):
    with pytest.raises(DocumentValidationError):
        DocumentLoader().from_string(markup)


def test_status_bar_errors_name_the_status_bar_tag():
    with pytest.raises(DocumentValidationError, match="status-bar accepts"):
        DocumentLoader().from_string('<ui><status-bar><label>Unslotted</label></status-bar></ui>')


@pytest.mark.asyncio
async def test_header_places_center_between_flexible_edges_and_flushes_right_slot():
    app = TextUI(DocumentLoader().from_string(MARKUP))
    async with app.run_test(size=(60, 5)) as pilot:
        await pilot.pause()
        header = app.document.get_by_id("top")
        left, center, right = header.slots
        assert left.region.x == header.region.x
        assert center.region.x > left.region.x
        assert right.region.x + right.region.width == header.region.x + header.region.width


@pytest.mark.asyncio
async def test_header_renders_a_linear_gradient_declared_in_tcss():
    app = TextUI(DocumentLoader().from_string('''<ui>
      <style>
        #top { background: linear-gradient(25deg, #173b6c, #376996, #12233d); }
      </style>
      <header id="top"><center><label>TextUI</label></center></header>
    </ui>'''))
    async with app.run_test():
        header = app.document.get_by_id("top")
        assert isinstance(header.render(), LinearGradient)
        assert all(isinstance(slot.render(), LinearGradient) for slot in header.slots)


@pytest.mark.asyncio
async def test_header_gradient_survives_a_style_preset_refresh():
    app = TextUI(DocumentLoader().from_string('''<ui>
      <style preset="compact" />
      <style>#top { background: linear-gradient(90deg, #173b6c, #12233d); }</style>
      <header id="top"><center><label>TextUI</label></center></header>
    </ui>'''))
    async with app.run_test() as pilot:
        header = app.document.get_by_id("top")
        assert header.render().angle == 90

        assert app.document.toggle_style_preset("compact") is False
        await pilot.pause()
        assert header.render().angle == 90
