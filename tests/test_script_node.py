import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from textui.textui import TextUI

def test_script_node_execution():
    markup = "<container><script>app.executed = True</script></container>"
    app = TextUI(markup)
    list(app.parse_markup())
    assert getattr(app, "executed", False) is True


def test_script_tag_ignored():
    markup = "<container><p></p><script>app.executed = True</script><p></p></container>"
    app = TextUI(markup)
    widgets = list(app.parse_markup())
    assert getattr(app, "executed", False) is True
    assert len(widgets) == 2
    assert all(w.__class__.__name__ == "P" for w in widgets)
