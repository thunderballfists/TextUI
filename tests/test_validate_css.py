import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from textui.validate_css import validate_css

import logging

css = """
#id_52999992-c6a0-4185-b641-962a53b0b30d {  width: 50; height: 50; }

Container {
  color: rgb( 12 ,45 , 4 , .23 );
}

  $border  :    wide   green   ;   

.error.disabled {
  background: darkred;
}

* {
  outline: solid red;
}

Button:disabled {
  background:   blue !important;
}

#dialog Horizontal Button {
  text-style: bold;
}

foo {
  border: $border;
}

#sidebar > Button {
  text-style: underline;
}
"""

expected = validate_css(css)


def test_validate_css():
    logging.getLogger().setLevel(logging.DEBUG)
    output = validate_css(css)

    logging.debug(output)
    assert output == expected


def test_uppercase_color_name_and_hex():
    css_upper = "foo { color: BLUE; background: #FFAABB; }"
    output = validate_css(css_upper)
    assert "color:BLUE" in output
    assert "background:#FFAABB" in output

