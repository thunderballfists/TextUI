import math
from xml.etree.ElementTree import Element

from textual import events
from textual.app import RenderResult, App
from textual.widget import Widget
from textual_imageview.img import ImageView

from PIL import Image
from pathlib import Path

from element_widget_definition import ElementWidgetDefinition


def preprocess_width_height(element: Element, _: App = None) -> None:
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
    app.stylesheet.add_source(css_data, path="embedded_style", is_default_css=False)
    app.stylesheet.parse()
    return False


class Img(Widget):
    DEFAULT_CSS = """
    Img {
        min-width: 8;
        min-height: 8;
    }
    """

    def __init__(self, src: str, height=100, width=100, *args, **kwargs):
        super().__init__(*args, **kwargs)
        image_path = Path(src)
        if not image_path.is_file():
            raise ValueError(f"Image file not found at '{src}'")

        self.image = ImageView(Image.open(image_path))

    def on_resize(self, event: events.Resize):
        self.image.set_container_size(event.size.width, event.size.height)
        self.refresh()

    def on_show(self):
        w, h = self.size.width, self.size.height
        img_w, img_h = self.image.size

        # Compute zoom such that image fits in container
        zoom_w = math.log(max(w, 1) / img_w, self.image.ZOOM_RATE)
        zoom_h = math.log((max(h, 1) * 2) / img_h, self.image.ZOOM_RATE)
        zoom = max(0, math.ceil(max(zoom_w, zoom_h)))
        self.image.set_zoom(zoom)

        # Position image in center of container
        img_w, img_h = self.image.zoomed_size
        self.image.origin_position = (-round((w - img_w) / 2), -round(h - img_h / 2))
        self.image.origin_position = (0, 0)
        self.image.set_container_size(w, h, maintain_center=False)

        self.refresh()

    def render(self) -> RenderResult:
        return self.image


class Div(Widget):
    DEFAULT_CSS = """
    Div {
        height: auto;
        layout: vertical;
        overflow: auto;
    }
    """


class P(Widget):
    DEFAULT_CSS = """
    P {
        height: auto;
        layout: vertical;
        overflow: auto;
        margin-top: 1em;
        margin-bottom: 1em;
    }
    """


class Span(Widget):
    DEFAULT_CSS = """
    Span {
        height: auto;
        layout: inline;
        overflow: auto;
    }
    """


HTML_WIDGETS = [
    ElementWidgetDefinition(tag="style", preprocessor=preprocess_style),
    ElementWidgetDefinition(tag="img", widget_class=Img, preprocessor=preprocess_width_height),
    ElementWidgetDefinition(tag="div", widget_class=Div),
    ElementWidgetDefinition(tag="p", widget_class=P),
    ElementWidgetDefinition(tag="span", widget_class=Span),
]
