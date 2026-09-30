import pytest
from textual.renderables.gradient import LinearGradient
from textual.geometry import Region

from textui import DocumentLoader, DocumentStyleError, DocumentValidationError, TextUI
from textui.styling import BackgroundGradient, GradientSlice


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
        assert all(isinstance(slot.render(), GradientSlice) for slot in header.slots)


@pytest.mark.asyncio
async def test_header_gradient_label_uses_the_background_geometry(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    app = TextUI(DocumentLoader().from_string('''<ui>
      <style>
        #top { background: linear-gradient(25deg, #173b6c, #376996, #12233d); }
      </style>
      <header id="top"><center><label id="title">TextUI</label></center></header>
    </ui>'''))
    async with app.run_test(size=(60, 5)):
        header = app.document.get_by_id("top")
        title = app.document.get_by_id("title")
        gradient = header.render()

        assert isinstance(gradient, BackgroundGradient)
        assert next(iter(title.render_lines(Region(0, 0, title.region.width, 1))[0])).style.bgcolor == gradient.color_at(
            title.region.x - header.region.x + .5,
            title.region.y - header.region.y + .5,
            header.content_size.width,
            header.content_size.height,
        )


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


@pytest.mark.asyncio
async def test_linear_gradient_rejects_a_non_bar_target():
    app = TextUI(DocumentLoader().from_string('''<ui>
      <style>#save { background: linear-gradient(90deg, #173b6c, #12233d); }</style>
      <button id="save">Save</button>
    </ui>'''))
    with pytest.raises(DocumentStyleError, match="header or status-bar"):
        async with app.run_test():
            pass


@pytest.mark.asyncio
async def test_header_gradient_allows_a_tcss_variable_preamble():
    app = TextUI(DocumentLoader().from_string('''<ui>
      <style>
        $accent: red;
        #top { background: linear-gradient(90deg, #173b6c, #12233d); }
      </style>
      <header id="top"><center><label>TextUI</label></center></header>
    </ui>'''))
    async with app.run_test():
        assert isinstance(app.document.get_by_id("top").render(), LinearGradient)


@pytest.mark.asyncio
async def test_solid_background_wins_over_an_earlier_gradient():
    app = TextUI(DocumentLoader().from_string('''<ui>
      <style>
        #top { background: linear-gradient(90deg, #173b6c, #12233d); }
        #top { background: red; }
      </style>
      <header id="top"><center><label>TextUI</label></center></header>
    </ui>'''))
    async with app.run_test():
        assert app.document.get_by_id("top").render() == ""


@pytest.mark.asyncio
async def test_header_gradient_mounts_inside_a_modal():
    app = TextUI(DocumentLoader().from_string('''<ui>
      <style>#modal-top { background: linear-gradient(90deg, #173b6c, #12233d); }</style>
      <button id="open">Open</button>
      <modal id="help"><header id="modal-top"><center><label>Help</label></center></header></modal>
    </ui>'''))
    async with app.run_test():
        result = app.document.push_modal("help")
        await result.mounted
        assert isinstance(app.document.get_by_id("modal-top").render(), LinearGradient)
        app.document.dismiss_modal()


@pytest.mark.asyncio
async def test_important_gradient_wins_over_a_later_solid_background():
    app = TextUI(DocumentLoader().from_string('''<ui>
      <style>
        #top { background: linear-gradient(90deg, #173b6c, #12233d) !important; }
        #top { background: red; }
      </style>
      <header id="top"><center><label>TextUI</label></center></header>
    </ui>'''))
    async with app.run_test():
        assert isinstance(app.document.get_by_id("top").render(), LinearGradient)


STATUS_BAR_WITH_BUTTONS = """<ui>
  <status-bar id="footer">
    <left><label>ready</label></left>
    <right>
      <button id="b1">Settings</button><button id="b2">Account</button>
      <button id="b3">Env</button><button id="b4">Quit</button>
    </right>
  </status-bar>
</ui>"""


@pytest.mark.asyncio
async def test_a_status_bar_with_nothing_in_the_centre_gives_its_controls_the_room_they_need():
    app = TextUI(DocumentLoader().from_string(STATUS_BAR_WITH_BUTTONS))
    async with app.run_test(size=(80, 8)) as pilot:
        await pilot.pause()
        for name in ("b1", "b2", "b3", "b4"):
            button = app.document.get_by_id(name)
            assert button.region.x + button.region.width <= 80, (name, button.region)


@pytest.mark.asyncio
@pytest.mark.parametrize("css", [
    "/* #missing { background: linear-gradient(0deg, red, blue); } */ Label { color: red; }",
    "/* gradients use { braces } */ #top { background: linear-gradient(0deg, red, blue); }",
    "#top /* bar { example } */ { background: linear-gradient(0deg, red, blue); }",
    "#top { background: /* tint */ linear-gradient(0deg, red, /* cool */ blue); }",
])
async def test_gradient_preprocessor_respects_native_tcss_comments(css):
    app = TextUI(DocumentLoader().from_string(f'''<ui><style>{css}</style>
      <header id="top"><center><label id="title">Title</label></center></header></ui>'''))
    async with app.run_test():
        header = app.document.get_by_id("top")
        if css.startswith("/* #missing"):
            assert header.render() == ""
            assert app.document.get_by_id("title").styles.color.hex == "#FF0000"
        else:
            assert isinstance(header.render(), BackgroundGradient)


@pytest.mark.asyncio
async def test_unterminated_tcss_comment_remains_a_contextual_style_error():
    app = TextUI(DocumentLoader().from_string('''<ui>
      <style>/* #top { background: linear-gradient(0deg, red, blue); }</style>
      <header id="top"/>
    </ui>''', source_name="comment.ui"))
    with pytest.raises(DocumentStyleError) as error:
        async with app.run_test():
            pass
    assert error.value.location.source == "comment.ui"


@pytest.mark.asyncio
@pytest.mark.parametrize("angle, colors", [(0, ("#4f00ae", "#4f00ae")), (90, ("#be003f", "#3f00be"))])
async def test_gradient_label_respects_cell_width_padding_alignment_and_lines(angle, colors, monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    app = TextUI(DocumentLoader().from_string(f'''<ui>
      <style>
        #top {{ width: 8; height: 2; background: linear-gradient({angle}deg, red, blue); }}
        #title {{ width: 6; height: 2; padding: 0 1; text-align: right; }}
      </style>
      <header id="top"><center><label id="title">Title</label></center></header>
    </ui>'''))
    async with app.run_test(size=(12, 4)) as pilot:
        app.document.get_by_id("title").update("界A\nB")
        await pilot.pause()
        strips = app.screen._compositor.render_strips()
        for y, (character, color) in enumerate(zip(("A", "B"), colors)):
            cell = strips[y].crop(5, 6)
            assert cell.text == character
            assert next(iter(cell)).style.bgcolor.triplet.hex == color


@pytest.mark.asyncio
async def test_gradient_follows_live_background_cascade_changes(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    app = TextUI(DocumentLoader().from_string('''<ui>
      <style>
        #top { background: linear-gradient(0deg, red, blue); }
        #top.-solid { background: green; }
      </style>
      <header id="top"><center><label>Title</label></center></header>
    </ui>'''))
    async with app.run_test(size=(40, 5)) as pilot:
        bar = app.document.get_by_id("top")
        assert isinstance(bar.render(), BackgroundGradient)
        bar.add_class("-solid")
        await pilot.pause()
        assert bar.styles.background.hex == "#008000"
        assert bar.render() == ""
        assert next(iter(app.screen._compositor.render_strips()[0].crop(10, 11))).style.bgcolor.triplet.hex == "#008000"
        bar.remove_class("-solid")
        await pilot.pause()
        assert isinstance(bar.render(), BackgroundGradient)
        assert next(iter(app.screen._compositor.render_strips()[0].crop(10, 11))).style.bgcolor.triplet.hex != "#008000"


@pytest.mark.asyncio
async def test_opaque_slot_background_covers_gradient_even_behind_labels(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    app = TextUI(DocumentLoader().from_string('''<ui>
      <style>
        #top { background: linear-gradient(0deg, red, blue); }
        #top > HeaderSlot.-center { background: green; }
        #title { padding: 0 1; }
      </style>
      <header id="top"><center><label id="title">Title</label></center></header>
    </ui>'''))
    async with app.run_test(size=(40, 5)) as pilot:
        await pilot.pause()
        title = app.document.get_by_id("title")
        row = app.screen._compositor.render_strips()[title.region.y]
        position = row.text.index("Title")
        assert row.crop(position, position + 1).text == "T"
        assert next(iter(row.crop(position, position + 1))).style.bgcolor.triplet.hex == "#008000"
        assert next(iter(row.crop(position - 1, position))).style.bgcolor.triplet.hex == "#008000"


@pytest.mark.asyncio
async def test_initial_solid_override_can_reveal_declared_gradient_later():
    app = TextUI(DocumentLoader().from_string('''<ui>
      <style>#top { background: linear-gradient(0deg, red, blue); }
             #top.-solid { background: green; }</style>
      <header id="top" class="-solid"><center><label>Title</label></center></header>
    </ui>'''))
    async with app.run_test() as pilot:
        bar = app.document.get_by_id("top")
        assert bar.render() == ""
        bar.remove_class("-solid")
        await pilot.pause()
        assert isinstance(bar.render(), BackgroundGradient)
