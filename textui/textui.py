import logging
import os
import uuid
from typing import Optional, List
from xml.etree.ElementTree import Element
from textual.app import App, ComposeResult
from textual.widget import Widget

from .validate_css import validate_css
from .widgets.widget_factory import ElementWidgetFactory
from lxml import html

class TextUI(App):
    def __init__(self, markup: str) -> None:
        super().__init__()
        self.widget_factory = ElementWidgetFactory()

        if os.path.isfile(markup):
            self.markup_path = os.path.abspath(markup)
            self.load_file(self.markup_path)
        else:
            self.markup = markup
            self.markup_path = None

    def load_file(self, file_name: str):
        with open(file_name, "r") as markup_file:
            self.markup = markup_file.read()

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

            inline_style_rule = validate_css(inline_style_rule)
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

    def parse_markup(self) -> ComposeResult:
        root = html.fromstring(self.markup)

        # root = ElementTree.fromstring(markup)
        for child in root:
            element = self.parse_element(child)
            if element is not None:
                yield element

    def compose(self) -> ComposeResult:
        composed_widgets = list(self.parse_markup())
        for widget in composed_widgets:
            logging.info(f"Composed widget: {widget}")
            yield widget

    def get_element_by_id(self, element_id: str) -> Widget:
        """Return a widget by its id.

        This is a convenience wrapper around :meth:`get_widget_by_id` to
        maintain backwards compatibility with older examples that refer to
        elements instead of widgets.
        """

        return self.get_widget_by_id(element_id)

    def get_elements_by_id(self, element_id: str) -> List[Widget]:
        """Return a list with the widget matching ``element_id``.

        Provided for API parity with the singular version. The list will
        contain the widget if found, otherwise it will be empty.
        """

        try:
            widget = self.get_widget_by_id(element_id)
        except Exception:
            return []
        return [widget]


if __name__ == "__main__":
    TextUI("../examples/sample_markup.xml").run()
