"""Run with ``python -I /path/to/tests/wheel_smoke.py`` after a clean wheel install."""

import asyncio
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import tempfile

import textui
from textui import (ActionContext, AttributeSpec, ComponentSpec, DocumentLoader, DocumentValidationError,
                    ElementNotFoundError, ProjectApp, ProjectSource, TextUI)
from textui.content import Children, Count, ElementRef, Only
from textui.metadata import Int
from textui.widgets.builtin_widgets import default_component_registry
from textual.containers import Vertical
from textual.content import Content
from textual.widgets import Label


async def main() -> None:
    package_path = Path(textui.__file__).resolve()
    assert package_path.is_relative_to(Path(sys.prefix).resolve()), package_path
    distribution = importlib.metadata.distribution("textui-markup")
    assert distribution.version == "0.7.0"
    assert distribution.metadata["Name"] == "textui-markup"
    assert any(
        entry.group == "console_scripts" and entry.name == "textui"
        and entry.value == "textui.__main__:main"
        for entry in distribution.entry_points
    )
    installed = {dist.metadata["Name"].lower().replace("_", "-") for dist in importlib.metadata.distributions()}
    assert "pillow" not in installed
    assert "textual-imageview" not in installed
    for module in ("PIL", "textual_imageview"):
        assert importlib.util.find_spec(module) is None

    registry = default_component_registry()
    described = registry.describe()
    json.dumps(described)
    assert registry.get("tabbed-content").describe()["content"]["rules"][0]["minimum"] == 1
    registry.register(ComponentSpec("count-label", lambda context: Label(str(context.attributes["count"])),
                                    attributes={"count": AttributeSpec(Int(minimum=0), required=True)}))
    registry.register(ComponentSpec("count-stack", lambda context: Vertical(*context.children), child_policy="widgets",
                                    content=Children((Count(minimum=1, message="counts required"),
                                                      Only((ElementRef("count-label"),), "count labels required")))))
    loader = DocumentLoader(registry)
    try:
        loader.from_string('<ui><count-stack/></ui>')
    except DocumentValidationError as error:
        assert error.message == "counts required"
    else:
        raise AssertionError("Installed content constraints were not enforced")
    metadata_app = TextUI(loader.from_string('<ui><count-stack><count-label id="count" count="3"/></count-stack></ui>'))
    async with metadata_app.run_test():
        assert str(metadata_app.document.get_by_id("count").render()) == "3"

    def save(context: ActionContext) -> None:
        name = context.document.get_by_id("name").value
        context.document.get_by_id("status").update(Content(f"Saved {name}"))

    document = DocumentLoader().from_string("""
    <ui>
      <style>#status { color: green; }</style>
      <vertical>
        <input id="name" value="wheel" />
        <button id="save" on-pressed="save">Save</button>
        <label id="status">Ready</label>
      </vertical>
    </ui>
    """)
    app = TextUI(document, actions={"save": save})
    async with app.run_test() as pilot:
        assert await pilot.click("#save")
        assert str(app.document.get_by_id("status").render()) == "Saved wheel"
    with tempfile.TemporaryDirectory() as directory:
        project = Path(directory)
        (project / "records.ui").write_text('''<component>
          <props><prop name="row-format" required="true"/></props>
          <list item-label="{row-format}" style="height: 3;"/>
        </component>''', encoding="utf-8")
        (project / "tabs.ui").write_text('''<component>
          <tabbed-content initial="home" style="height: 5; width: 40;">
            <tab-pane id="home" title="Home"><label>Home</label></tab-pane>
            <tab-pane id="details" title="Details" accelerator="d" accelerator-scope="document"><label>Details</label></tab-pane>
          </tabbed-content>
        </component>''', encoding="utf-8")
        (project / "app.ui").write_text('''<ui>
          <script src="controller.py"/>
          <component src="records.ui" as="record-list"/>
          <component src="tabs.ui" as="detail-tabs"/>
          <vertical>
            <button id="go" on-pressed="click">Go</button>
            <record-list id="records" row-format="{name}: {count:03d}"/>
            <log id="stream" style="height: 4;"/>
          </vertical>
          <modal id="details">
            <detail-tabs id="modal-tabs"/>
            <button id="close" on-pressed="close">Close</button>
          </modal>
        </ui>''', encoding="utf-8")
        (project / "controller.py").write_text('''from textui import action

async def on_ready():
    await window.document.get_by_id("records").set_items([{"name": "Alpha", "count": 2}])
    window.document.get_by_id("stream").append_inline("wheel ")

@action
async def click(context):
    window.app.clicked = True
    window.document.get_by_id("stream").append_inline("ready")
    window.document.get_by_id("stream").commit_line()
    await context.push_modal("details")

@action
def close(context):
    context.dismiss_modal("closed")
''', encoding="utf-8")
        checked = subprocess.run(
            [sys.executable, "-I", "-m", "textui", "check", str(project / "app.ui")],
            cwd=directory, capture_output=True, text=True,
        )
        assert checked.returncode == 0, checked.stderr
        assert str(project / "app.ui") in checked.stdout
        assert checked.stderr == ""
        project_app = ProjectApp(ProjectSource.discover(project / "app.ui"))
        async with project_app.run_test() as pilot:
            records = project_app.document.get_by_id("records")
            assert str(records.items[0].children[0].render()) == "Alpha: 002"
            assert await pilot.click(records.items[0].children[0], offset=(1, 0))
            assert records.selected == {"name": "Alpha", "count": 2}
            prior_tabs = None
            for _ in range(2):
                await pilot.press("d")  # Dormant modal bindings must be unavailable.
                assert await pilot.click("#go")
                await pilot.pause()
                assert project_app.clicked is True
                assert project_app.screen.id == "details"
                tabs = project_app.document.get_by_id("modal-tabs")
                assert tabs is not prior_tabs
                assert tabs.active.endswith("_home")
                await pilot.press("d")
                assert tabs.active.endswith("_details")
                try:
                    project_app.document.get_by_id(tabs.active)
                except ElementNotFoundError:
                    pass
                else:
                    raise AssertionError("Component-private IDs leaked through public lookup")
                assert await pilot.click("#close")
                await pilot.pause()
                assert len(project_app.screen_stack) == 1
                prior_tabs = tabs
            stream = project_app.document.get_by_id("stream")
            assert [line.text.rstrip() for line in stream.lines] == ["wheel ready", "ready"]
    controls = DocumentLoader().from_string('''<ui>
      <select id="state" value="new" allow-blank="false"><option value="new">New</option></select>
      <switch id="enabled" value="true" />
      <text-area id="notes">line one\nline two</text-area>
      <tabbed-content id="tabs" initial="home"><tab-pane id="home" title="Home"><label>Welcome</label></tab-pane></tabbed-content>
      <radio-set id="choice"><radio-button id="low">Low</radio-button><radio-button id="high" value="true">High</radio-button></radio-set>
      <collapsible id="details" title="Details" collapsed="false"><label>More</label></collapsible>
      <progress-bar id="work" total="10" progress="2" />
      <rule id="divider" line-style="dashed" />
      <data-table id="jobs"><column key="name">Name</column><row key="one"><cell>One</cell></row></data-table>
      <tree id="files" label="Files"><tree-node key="app" label="app.py"/></tree>
    </ui>''')
    controls_app = TextUI(controls)
    async with controls_app.run_test():
        assert controls_app.document.get_by_id("state").value == "new"
        assert controls_app.document.get_by_id("enabled").value is True
        assert controls_app.document.get_by_id("notes").text == "line one\nline two"
        assert controls_app.document.get_by_id("tabs").active == "home"
        assert controls_app.document.get_by_id("choice").pressed_button.id == "high"
        assert controls_app.document.get_by_id("details").collapsed is False
        assert controls_app.document.get_by_id("work").progress == 2.0
        assert controls_app.document.get_by_id("divider").line_style == "dashed"
        assert controls_app.document.get_by_id("jobs").get_cell("one", "name").plain == "One"
        assert controls_app.document.get_by_id("files").root.children[0].data == "app"
    assert not any(name == "PIL" or name.startswith("PIL.") or name == "textual_imageview" or name.startswith("textual_imageview.") for name in sys.modules)
    print(f"Clean wheel headless smoke passed: {package_path}")
    print({name: importlib.metadata.version(name) for name in ("textui-markup", "textual", "lxml")})


if __name__ == "__main__":
    asyncio.run(main())
