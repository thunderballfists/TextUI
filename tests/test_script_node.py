import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from textui.textui import TextUI


def test_script_node_execution_with_language():
    markup = "<container><script language='python'>app.executed = True</script></container>"
    app = TextUI(markup)
    list(app.parse_markup())
    assert getattr(app, "executed", False) is True


def test_script_node_default_language():
    markup = "<container><script>app.default_executed = True</script></container>"
    app = TextUI(markup)
    list(app.parse_markup())
    assert getattr(app, "default_executed", False) is True


def test_script_node_unknown_language():
    markup = "<container><script language='javascript'>app.js_executed = True</script></container>"
    app = TextUI(markup)
    list(app.parse_markup())
    assert getattr(app, "js_executed", False) is False


def test_script_tag_ignored():
    markup = "<container><p></p><script language='python'>app.executed = True</script><p></p></container>"
    app = TextUI(markup)
    widgets = list(app.parse_markup())
    assert getattr(app, "executed", False) is True
    assert len(widgets) == 2
    assert all(w.__class__.__name__ == "P" for w in widgets)
