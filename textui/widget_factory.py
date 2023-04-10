from typing import Optional
from xml.etree.ElementTree import Element
from textual.widget import Widget

from builtin_widgets import BUILT_IN_WIDGETS
from element_widget_definition import ElementWidgetDefinition
from html_widgets import HTML_WIDGETS


class ElementWidgetFactory:
    def __init__(self):
        self._definitions = {}

        # Register built-in widgets
        for definition in BUILT_IN_WIDGETS:
            self.register(definition)

        # Register html widgets
        for definition in HTML_WIDGETS:
            self.register(definition)

    def get_definition(self, tag):
        return self._definitions.get(tag)

    def register(self, definition: ElementWidgetDefinition) -> None:
        self._definitions[definition.tag] = definition

    def create(self, tag: str, element: Element) -> Optional[Widget]:
        definition = self._definitions.get(tag)

        if not definition:
            return None

        widget_class = definition.widget_class
        if element.text is not None:
            widget = widget_class(element.text, **element.attrib)
        else:
            widget = widget_class(**element.attrib)
        return widget
