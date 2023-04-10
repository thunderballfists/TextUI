import logging
import uuid
from typing import Union, Optional
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from textual.app import App, ComposeResult
from textual.widget import Widget
from widget_factory import ElementWidgetFactory

logging.getLogger().setLevel(logging.DEBUG)


class TextUI(App):
    def __init__(self, markup: str) -> None:
        super().__init__()
        self.markup = markup
        self.widget_factory = ElementWidgetFactory()

    def parse_element(self, element: Element) -> Optional[Widget]:
        tag = element.tag.lower()

        definition = self.widget_factory.get_definition(tag)
        if not definition:
            return None

        if definition.element_preprocessor:
            preprocess_result = definition.element_preprocessor(element, self)
            if not preprocess_result:
                return None

        inline_style = element.attrib.pop("style", None)
        class_list = element.attrib.pop("class", None)

        if tag != 'footer':
            unique_id = "id_" + str(uuid.uuid4())
            if "id" not in element.attrib:
                element.attrib["id"] = unique_id

        widget = self.widget_factory.create(tag, element)
        if not widget:
            return None

        if class_list:
            widget.add_class(class_list)

        if inline_style:
            if tag == "footer":
                selector = "footer"
            else:
                selector = f"#{element.attrib['id']}"
            inline_style_rule = f"{selector} {{ {inline_style} }}"
            self.stylesheet.add_source(inline_style_rule, path=f"{widget.name}_inline_style")
            self.stylesheet.parse()

        # Process child elements for any widget
        for child in element:
            child_widget = self.parse_element(child)
            if child_widget is not None:
                try:
                    widget.compose_add_child(child_widget)
                except AttributeError:
                    raise ValueError(f"{widget.__class__.__name__} cannot have child elements")

        return widget

    def parse_markup(self, markup: str) -> ComposeResult:
        root = ElementTree.fromstring(markup)
        for child in root:
            element = self.parse_element(child)
            if element is not None:
                yield element

    def compose(self) -> ComposeResult:
        composed_widgets = list(self.parse_markup(self.markup))
        for widget in composed_widgets:
            logging.info(f"Composed widget: {widget}")
            yield widget


if __name__ == "__main__":
    with open("sample_markup.xml", "r") as markup_file:
        markup = markup_file.read()
    TextUI(markup).run()
