from typing import Optional, Type, Callable, Any, Union
from xml.etree.ElementTree import Element

from textual.widget import Widget


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
