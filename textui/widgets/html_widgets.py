import math

from textual import events
from textual.app import RenderResult
from textual.widget import Widget
from textual_imageview.img import ImageView

from PIL import Image
from pathlib import Path


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
        margin-top: 1;
        margin-bottom: 1;
    }
    """


class Span(Widget):
    DEFAULT_CSS = """
    Span {
        height: auto;
        overflow: auto;
    }
    """
