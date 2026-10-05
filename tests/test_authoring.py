import json
from pathlib import Path

from lxml import etree

from textui.__main__ import main
from textui.widgets.builtin_widgets import default_component_registry


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "docs/markup-reference.md", "spec/textui.xsd", "spec/textui-authoring.xsd",
    "spec/vscode-html-custom-data.json", "spec/web-types.json",
    "llms.txt", "docs/llm-reference.md",
}


def test_generator_is_deterministic_and_artifacts_do_not_drift():
    from textui.authoring import artifacts

    generated = artifacts()
    assert set(generated) == EXPECTED
    assert generated == artifacts()
    for path, content in generated.items():
        assert content.endswith("\n")
        assert (ROOT / path).read_text(encoding="utf-8") == content, path
    for path in ("spec/textui.xsd", "spec/textui-authoring.xsd"):
        etree.XMLSchema(etree.fromstring(generated[path].encode()))


def test_completions_cover_registry_attributes_events_and_values():
    from textui.authoring import artifacts

    outputs = artifacts()
    data = json.loads(outputs["spec/vscode-html-custom-data.json"])
    web = json.loads(outputs["spec/web-types.json"])
    assert data["version"] == 1.1
    tags = {tag["name"]: tag for tag in data["tags"]}
    web_tags = {tag["name"]: tag for tag in web["contributions"]["html"]["elements"]}
    for spec in default_component_registry().describe()["components"]:
        assert spec["tag"] in tags and spec["tag"] in web_tags
        names = {attr["name"]: attr for attr in tags[spec["tag"]]["attributes"]}
        assert set(spec["attributes"]) <= names.keys()
        assert {f"on-{name}" for name in spec["events"]} <= names.keys()
        for name, attr in spec["attributes"].items():
            if "values" in attr["type"]:
                assert [v["name"] for v in names[name]["values"]] == attr["type"]["values"]
        assert f"### `<{spec['tag']}>`" in outputs["docs/markup-reference.md"]


def test_bundled_examples_match_repository_sources():
    from textui.authoring.facts import EXAMPLES

    assert EXAMPLES
    for path, markup in EXAMPLES.items():
        assert (ROOT / path).read_text(encoding="utf-8") == markup
        assert markup in __import__("textui.authoring", fromlist=["artifacts"]).artifacts()["docs/llm-reference.md"]


def test_spec_cli_works_from_arbitrary_directory(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["spec", "--output", "generated"]) == 0
    assert "Generated" in capsys.readouterr().out
    for relative in EXPECTED:
        assert (tmp_path / "generated" / relative).is_file()


def test_generator_never_calls_widget_factories(monkeypatch):
    from dataclasses import replace
    from textui.authoring import artifacts
    from textui.registry import ComponentRegistry
    import textui.authoring

    registry = ComponentRegistry()

    def forbidden(*args, **kwargs):
        raise AssertionError("generator called a factory")

    for spec in default_component_registry().snapshot().values():
        registry.register(replace(spec, factory=forbidden))
    monkeypatch.setattr(textui.authoring, "default_component_registry", lambda: registry)
    assert set(artifacts()) == EXPECTED
