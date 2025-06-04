
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
    app.run()
```

License
-------

TextUI is released under the [MIT License](LICENSE).

Credits
-------

TextUI is built on top of the [Textual](https://github.com/Textualize/textual) framework by [Will McGugan](https://github.com/willmcgugan).
