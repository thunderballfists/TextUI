class Document:
    """Helper providing DOM-like methods for TextUI applications."""

    def __init__(self, app):
        self.app = app

    def get_element_by_id(self, id):
        """Return the first widget with the given id."""
        return self.app.query_one(f"#{id}")

    # Alias
    get_widget_by_id = get_element_by_id

    def get_elements_by_class_name(self, cls):
        """Return widgets matching the given class name."""
        return self.app.query(f".{cls}")

    def get_elements_by_tag_name(self, tag):
        """Return widgets matching the given tag name."""
        return self.app.query(tag)

    def add_event_listener(self, widget, event_cls, callback):
        """Register an event handler on ``widget``."""
        widget.on(event_cls, callback)
