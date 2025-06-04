
This is very early and so far can render markup with styles both in a style tag or inline.
Scripting and event handling are up next. Some of the following is more aspirational atm :


TextUI: Build Text-based User Interfaces with HTML-like Syntax
==============================================================

TextUI is a library built on top of the great and powerful [Textual](https://github.com/willmcgugan/textual) framework to create rich terminal applications using an HTML-like syntax. The goal of this project is to make building text user interfaces more accessible and easier to iterate, especially for those familiar with HTML based applications.



Features/Goals
--------

- Create terminal applications using a familiar HTML-like syntax
- Easily style your applications with CSS
- Event handling and scripting support (with Python)
- Modular design for easy component addition and modification
- Extensive documentation and examples to help you get started quickly


Usage
-----

To use TextUI, review `examples/sample_markup.xml` or the module `textui/textui.py` for now.
```

...


    markup = """
<container>
    <style>
        .test {
            background: blue;
        }
        Header {
            background: green;
            color:blue;
        }
        Footer {
            background: blue;
        }
        .accent {
            background: red;
        }
    </style>
    <header/>
    <label id="accent">Welcome to the sample XML file</label>
    <label class="accent">label with accent styling.</label>
    <label class="test">label with blue styling.</label>
    <button class="accent">This button has the "accent" class, which applies HSL color.</button>
    <button>This button has default styling.</button>
    <footer/>
</container>
"""

    app = MyApp(markup)
    label = app.get_element_by_id("accent")
    label_list = app.get_elements_by_id("accent")
    app.run()
```

Logging
-------

TextUI relies on Python's standard `logging` module. The package does not set a
global logging level, so applications should configure logging as desired:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Enabling debug output can be helpful when troubleshooting markup or CSS issues.

Document and Window Helpers
---------------------------

Scripts executed via `<script>` tags receive a ``document`` helper and ``window``
alias. ``window`` simply refers to the ``TextUI`` instance while ``document``
offers DOM-like utilities:

``get_element_by_id(id)`` / ``get_widget_by_id(id)``
    Retrieve a widget by its ``id``.
``get_elements_by_class_name(cls)``
    Query widgets with the given class.
``get_elements_by_tag_name(tag)``
    Query widgets by tag name.
``add_event_listener(widget, event_cls, callback)``
    Attach a handler to a widget event.

Example:

```python
markup = "<container><button id='ok'>OK</button></container>"
app = TextUI(markup)

def on_press(event):
    print("button pressed")

button = app.document.get_widget_by_id("ok")
app.document.add_event_listener(button, Button.Pressed, on_press)
```


License
-------

TextUI is released under the [MIT License](LICENSE).

Credits
-------

TextUI is built on top of the [Textual](https://github.com/Textualize/textual) framework by [Will McGugan](https://github.com/willmcgugan).
