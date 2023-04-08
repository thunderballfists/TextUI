import sys
import logging
import uuid
from typing import Union
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from textual.app import App, ComposeResult
from textual.containers import Container, Center, Content, Grid, Horizontal, HorizontalScroll, Middle, Vertical, \
    VerticalScroll
from textual.widget import Widget
from textual.widgets import Header, Footer, Button, Checkbox, ContentSwitcher, DataTable, DirectoryTree, Input, Label, \
    ListItem, ListView, LoadingIndicator, Markdown, MarkdownViewer, OptionList, Placeholder, Pretty, RadioButton, \
    RadioSet, Static, Switch, TabbedContent, TabPane, Tab, Tabs, TextLog, Tree, Welcome

logging.getLogger().setLevel(logging.DEBUG)

containers = ["Center", "Container", "Content", "Grid", "Horizontal", "HorizontalScroll", "Middle", "Vertical", "VerticalScroll"]

TAG_TO_CLASS = {
    "center": Center,
    "container": Container,
    "content": Content,
    "grid": Grid,
    "horizontal": Horizontal,
    "horizontal_scroll": HorizontalScroll,
    "middle": Middle,
    "vertical": Vertical,
    "vertical_scroll": VerticalScroll,
    "button": Button,
    "checkbox": Checkbox,
    "content_switcher": ContentSwitcher,
    "data_table": DataTable,
    "directory_tree": DirectoryTree,
    "footer": Footer,
    "header": Header,
    "input": Input,
    "label": Label,
    "list_item": ListItem,
    "list_view": ListView,
    "loading_indicator": LoadingIndicator,
    "markdown": Markdown,
    "markdown_viewer": MarkdownViewer,
    "option_list": OptionList,
    "placeholder": Placeholder,
    "pretty": Pretty,
    "radio_button": RadioButton,
    "radio_set": RadioSet,
    "static": Static,
    "switch": Switch,
    "tabbed_content": TabbedContent,
    "tab_pane": TabPane,
    "tab": Tab,
    "tabs": Tabs,
    "text_log": TextLog,
    "tree": Tree,
    "welcome": Welcome,
}

def parse_element(element: Element, app: App) -> Union[Widget, Container, None]:
    tag = element.tag.lower()

    if tag == "style":
        css_data = element.text
        app.stylesheet.add_source(css_data, path="embedded_style", is_default_css=False)
        app.stylesheet.parse()
        return None

    widget_class = TAG_TO_CLASS.get(tag)

    if not widget_class:
        raise ValueError(f"Unknown element: {tag}")

    if tag != "footer":
        # Generate a unique ID and set it as the `id` attribute if not present
        unique_id = "id_"+str(uuid.uuid4())
        if "id" not in element.attrib:
            element.attrib["id"] = unique_id

    inline_style = element.attrib.pop("style", None)
    class_list = element.attrib.pop("class", None)
    if tag == "static" or tag == "button" or tag == "label":
        widget = widget_class(element.text,  **element.attrib)
    else:
        widget = widget_class(**element.attrib)

    if class_list:
        widget.add_class(class_list)

    if inline_style:
        if tag == "footer":
            selector = "footer"
        else:
            # Normalize the spaces in the inline style
            selector = f"#{element.attrib['id']}"
        inline_style_rule = f"{selector} {{ {inline_style} }}"
        app.stylesheet.add_source(inline_style_rule, path=f"{widget.name}_inline_style")
        app.stylesheet.parse()

    if widget.__class__.__name__ in containers:
        for child in element:
            child_widget = parse_element(child, app)
            if child_widget is not None:
                widget.compose_add_child(child_widget)

    return widget

def parse_markup(markup: str, app:App) -> ComposeResult:
    root = ElementTree.fromstring(markup)
    for child in root:
        element = parse_element(child, app)
        if element is not None:
            yield element

class MyApp(App):
    def __init__(self, markup: str) -> None:
        super().__init__()
        self.markup = markup

    def compose(self) -> ComposeResult:
        composed_widgets = list(parse_markup(self.markup, self))
        for widget in composed_widgets:
            logging.info(f"Composed widget: {widget}")
            yield widget


if __name__ == "__main__":
    with open("sample_markup.xml", "r") as markup_file:
        markup = markup_file.read()
    MyApp(markup).run()
