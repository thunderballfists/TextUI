from typing import Optional, Type, Callable, Any, Union
from xml.etree.ElementTree import Element

from textual.app import App
from textual.widget import Widget

import os

from validate_css import validate_css


def get_absolute_path(file_path, abs_path):
    if os.path.isabs(file_path):
        return file_path
    else:
        return os.path.abspath(os.path.join(os.path.dirname(abs_path), file_path))


def preprocess_src(element: Element, app: App):
    src = element.attrib.get('src')
    if src:
        if app.markup_path:
            src = get_absolute_path(src, app.markup_path)
        element.attrib["src"] = src


def preprocess_width_height(element: Element, _: App = None) -> bool:
    width = element.attrib.pop("width", None)
    height = element.attrib.pop("height", None)

    if width or height:
        style = element.attrib.get("style", "")
        if style and not style.endswith(";"):
            style += ";"
        if width:
            style += f" width: {width};"
        if height:
            style += f" height: {height};"
        element.attrib["style"] = style
    return True


def preprocess_style(element: Element, app: App) -> bool:
    css_data = element.text

    css_data = validate_css(css_data)
    app.stylesheet.add_source(css_data, path="embedded_style", is_default_css=False)
    app.stylesheet.parse()
    return False


class ElementWidgetDefinition:
    def __init__(
            self,
            tag: str,
            widget_class: Optional[Type[Widget]] = None,
            preprocessor: Optional[Callable[[Element, Any], Union[bool, None]]] = None,
            app: Optional[Any] = None,
    ):
        self.tag = tag
        self.widget_class = widget_class
        self.element_preprocessor = preprocessor
        self.app = app
