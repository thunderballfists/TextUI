import pytest

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
