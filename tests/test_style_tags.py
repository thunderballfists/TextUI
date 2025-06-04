import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from textui.textui import TextUI


def test_multiple_style_tags():
    markup = "<container><style>.one {color: red;}</style><style>.two {color: blue;}</style></container>"
    app = TextUI(markup)
    list(app.parse_markup())

    sources = list(app.stylesheet.source.values())
    assert len(sources) == 2
    assert any('.one' in source.content for source in sources)
    assert any('.two' in source.content for source in sources)
