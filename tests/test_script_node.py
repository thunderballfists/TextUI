from textui.textui import TextUI

def test_script_node_execution():
    markup = "<container><script>app.executed = True</script></container>"
    app = TextUI(markup)
    list(app.parse_markup())
    assert getattr(app, "executed", False) is True
