"""Run with ``python -I /path/to/tests/wheel_smoke.py`` after a clean wheel install."""

import asyncio
import importlib.metadata
import importlib.util
from pathlib import Path
import sys
import tempfile

import textui
from textui import ActionContext, DocumentLoader, ProjectApp, ProjectSource, TextUI
from textual.content import Content


async def main() -> None:
    package_path = Path(textui.__file__).resolve()
    assert package_path.is_relative_to(Path(sys.prefix).resolve()), package_path
    assert importlib.metadata.version("textui") == "0.6.0"
    installed = {dist.metadata["Name"].lower().replace("_", "-") for dist in importlib.metadata.distributions()}
    assert "pillow" not in installed
    assert "textual-imageview" not in installed
    for module in ("PIL", "textual_imageview"):
        assert importlib.util.find_spec(module) is None

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
        (project / "app.ui").write_text('<ui><script src="controller.py"/><button id="go" on-pressed="click">Go</button></ui>', encoding="utf-8")
        (project / "controller.py").write_text('from textui import action\n@action\ndef click():\n    window.app.clicked = True\n', encoding="utf-8")
        project_app = ProjectApp(ProjectSource.discover(project / "app.ui"))
        async with project_app.run_test() as pilot:
            assert await pilot.click("#go")
            assert project_app.clicked is True
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
    print({name: importlib.metadata.version(name) for name in ("textui", "textual", "lxml")})


if __name__ == "__main__":
    asyncio.run(main())
