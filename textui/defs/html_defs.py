from xml.etree.ElementTree import Element

from textual.app import App
from textual.containers import Container

from defs.element_widget_definition import ElementWidgetDefinition, preprocess_width_height, preprocess_style, \
    preprocess_src
from widgets.html_widgets import Img, Div, P, Span


def preprocess_img(element: Element, app: App) -> bool:
    preprocess_width_height(element, app)
    preprocess_src(element, app)
    return True


HTML_DEFS = [
    ElementWidgetDefinition(tag="html", widget_class=Container),
    ElementWidgetDefinition(tag="style", preprocessor=preprocess_style),
    ElementWidgetDefinition(tag="img", widget_class=Img, preprocessor=preprocess_img),
    ElementWidgetDefinition(tag="div", widget_class=Div),
    ElementWidgetDefinition(tag="p", widget_class=P),
    ElementWidgetDefinition(tag="span", widget_class=Span),
]
