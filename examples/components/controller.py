from textui import action


@action
def open_alpha():
    window.document.get_by_id("alpha").add_class("opened")
