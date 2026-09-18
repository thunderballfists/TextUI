"""Run with ``python -I /path/to/tests/wheel_smoke.py`` after a clean wheel install."""

import asyncio
import importlib.metadata
import importlib.util
from pathlib import Path
import sys

import textui
from textui import ActionContext, DocumentLoader, TextUI
from textual.content import Content


async def main() -> None:
    package_path = Path(textui.__file__).resolve()
    assert package_path.is_relative_to(Path(sys.prefix).resolve()), package_path
    assert importlib.metadata.version("textui") == "0.2.1"
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
    assert not any(name == "PIL" or name.startswith("PIL.") or name == "textual_imageview" or name.startswith("textual_imageview.") for name in sys.modules)
    print(f"Clean wheel headless smoke passed: {package_path}")
    print({name: importlib.metadata.version(name) for name in ("textui", "textual", "lxml")})


if __name__ == "__main__":
    asyncio.run(main())
