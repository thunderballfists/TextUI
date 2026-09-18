import logging
import re

# Define the dictionaries for style and values
styles = {
    "align": "<horizontal>\\s+<vertical>",
    "align-horizontal": "<horizontal>",
    "align-vertical": "<vertical>",
    "background": "<color>(\\s+<percentage>)?",
    "border": "(<border>)?(\\s+<color>)?(\\s+<percentage>)?",
    "border-top": "(<border>)?(\\s+<color>)?(\\s+<percentage>)?",
    "border-right": "(<border>)?(\\s+<color>)?(\\s+<percentage>)?",
    "border-bottom": "(<border>)?(\\s+<color>)?(\\s+<percentage>)?",
    "border-left": "(<border>)?(\\s+<color>)?(\\s+<percentage>)?",
    "border-subtitle-align": "<horizontal>",
    "border-title-align": "<horizontal>",
    "box-sizing": "border-box|content-box",
    "color": "(<color>|auto)(\\s+<percentage>)?",
    "content-align": "<horizontal>\\s+<vertical>",
    "content-align-horizontal": "<horizontal>",
    "content-align-vertical": "<vertical>",
    "display": "block|none",
    "dock": "bottom|left|right|top",
    "column-span": "<integer>",
    "grid-columns": "<scalar>+",
    "grid-gutter": "<scalar>(\\s+<scalar>)?",
    "grid-rows": "<scalar>+",
    "grid-size": "<integer>(\\s+<integer>)?",
    "row-span": "<integer>",
    "height": "<scalar>",
    "layer": "<name>",
    "layers": "<name>+",
    "layout": "grid|horizontal|vertical",
    "link-background": "<color>(\\s+<percentage>)?",
    "link-color": "<color>(\\s+<percentage>)?",
    "link-style": "<text-style>",
    "link-hover-background": "<color>(\\s+<percentage>)?",
    "link-hover-color": "<color>(\\s+<percentage>)?",
    "link-hover-style": "<text-style>",
    "margin": "<integer>|<integer>\\s+<integer>|<integer>\\s+<integer>\\s+<integer>\\s+<integer>",
    "margin-top": "<integer>",
    "margin-right": "<integer>",
    "margin-bottom": "<integer>",
    "margin-left": "<integer>",
    "max-height": "<scalar>",
    "max-width": "<scalar>",
    "min-height": "<scalar>",
    "min-width": "<scalar>",
    "offset": "<scalar>\\s+<scalar>",
    "offset-x": "<scalar>",
    "offset-y": "<scalar>",
    "opacity": "<number>|<percentage>",
    "outline": "(<border>)?(\\s+<color>)?",
    "outline-top": "(<border>)?(\\s+<color>)?",
    "outline-right": "(<border>)?(\\s+<color>)?",
    "outline-bottom": "(<border>)?(\\s+<color>)?",
    "outline-left": "(<border>)?(\\s+<color>)?",
    "overflow": "<overflow>\\s+<overflow>",
    "overflow-x": "<overflow>",
    "overflow-y": "<overflow>",
    "padding": "<integer>|<integer>\\s+<integer>|<integer>\\s+<integer>\\s+<integer>\\s+<integer>",
    "padding-top": "<integer>",
    "padding-right": "<integer>",
    "padding-bottom": "<integer>",
    "padding-left": "<integer>",
    "scrollbar-background": "<color>(\\s+<percentage>)?",
    "scrollbar-background-active": "<color>(\\s+<percentage>)?",
    "scrollbar-background-hover": "<color>(\\s+<percentage>)?",
    "scrollbar-color": "<color>(\\s+<percentage>)?",
    "scrollbar-color-active": "<color>(\\s+<percentage>)?",
    "scrollbar-color-hover": "<color>(\\s+<percentage>)?",
    "scrollbar-corner-color": "<color>(\\s+<percentage>)?",
    "scrollbar-gutter": "auto|stable",
    "scrollbar-size": "<integer>\\s+<integer>",
    "scrollbar-size-horizontal": "<integer>",
    "scrollbar-size-vertical": "<integer>",
    "text-align": "<text-align>",
    "text-opacity": "<number>|<percentage>",
    "text-style": "<text-style>",
    "tint": "<color>(\\s+<percentage>)?",
    "visibility": "hidden|visible",
    "width": "<scalar>|<percentage>",
}

named_web_colors_regex = "aliceblue|ansi_black|ansi_blue|ansi_bright_black|ansi_bright_blue|ansi_bright_cyan" \
                         "|ansi_bright_green|ansi_bright_magenta|ansi_bright_red|ansi_bright_white|ansi_bright_yellow" \
                         "|ansi_cyan|ansi_green|ansi_magenta|ansi_red|ansi_white|ansi_yellow|antiquewhite|aqua" \
                         "|aquamarine|azure|beige|bisque|black|blanchedalmond|blue|blueviolet|brown|burlywood" \
                         "|cadetblue|chartreuse|chocolate|coral|cornflowerblue|cornsilk|crimson|cyan|darkblue" \
                         "|darkcyan|darkgoldenrod|darkgray|darkgreen|darkgrey|darkkhaki|darkmagenta|darkolivegreen" \
                         "|darkorange|darkorchid|darkred|darksalmon|darkseagreen|darkslateblue|darkslategray" \
                         "|darkslategrey|darkturquoise|darkviolet|deeppink|deepskyblue|dimgray|dimgrey|dodgerblue" \
                         "|firebrick|floralwhite|forestgreen|fuchsia|gainsboro|ghostwhite|gold|goldenrod|gray|green" \
                         "|greenyellow|grey|honeydew|hotpink|indianred|indigo|ivory|khaki|lavender|lavenderblush" \
                         "|lawngreen|lemonchiffon|lightblue|lightcoral|lightcyan|lightgoldenrodyellow|lightgray" \
                         "|lightgreen|lightgrey|lightpink|lightsalmon|lightseagreen|lightskyblue|lightslategray" \
                         "|lightslategrey|lightsteelblue|lightyellow|lime|limegreen|linen|magenta|maroon" \
                         "|mediumaquamarine|mediumblue|mediumorchid|mediumpurple|mediumseagreen|mediumslateblue" \
                         "|mediumspringgreen|mediumturquoise|mediumvioletred|midnightblue|mintcream|mistyrose" \
                         "|moccasin|navajowhite|navy|oldlace|olive|olivedrab|orange|orangered|orchid|palegoldenrod" \
                         "|palegreen|paleturquoise|palevioletred|papayawhip|peachpuff|peru|pink|plum|powderblue" \
                         "|purple|rebeccapurple|red|rosybrown|royalblue|saddlebrown|salmon|sandybrown|seagreen" \
                         "|seashell|sienna|silver|skyblue|slateblue|slategray|slategrey|snow|springgreen|steelblue" \
                         "|tan|teal|thistle|tomato|turquoise|violet|wheat|white|whitesmoke|yellow|yellowgreen"
named_ansi_colors_regex = "ansi_black|ansi_red|ansi_green|ansi_yellow|ansi_blue|ansi_magenta|ansi_cyan|ansi_white" \
                          "|ansi_bright_black|ansi_bright_red|ansi_bright_green|ansi_bright_yellow|ansi_bright_blue" \
                          "|ansi_bright_magenta|ansi_bright_cyan|ansi_bright_white"

color_value_regex = (
        "(#(?:[0-9a-f]{6}|[0-9a-f]{3})(?:[0-9a-f]{2})?|" +
        "rgba?\\(\\s*(?:\\d{1,3}\\s*,\\s*){2}\\d{1,3}\\s*(?:,\\s*(?:0?\\.\\d{1,2}|1(\\.0)?|0))?\\s*\\)|" +
        "hsla?\\(\\s*\\d{1,3}\\s*(?:,\\s*\\d{1,3}%\\s*){2}(?:,\\s*(?:0?\\.\\d{1,2}|1(\\.0)?|0))?\\s*\\)|"
        + named_web_colors_regex + "|transparent|" + named_ansi_colors_regex + ")"
)

# Compiled regex objects for color validation
named_web_colors_pattern = re.compile(named_web_colors_regex, re.IGNORECASE)
named_ansi_colors_pattern = re.compile(named_ansi_colors_regex, re.IGNORECASE)
color_value_pattern = re.compile(color_value_regex, re.IGNORECASE)

values = {
    "<border>": "ascii|blank|dashed|double|heavy|hidden|hkey|inner|none|outer|round|solid|tall|thick|vkey|wide",
    "<color>": color_value_pattern,
    "<horizontal>": "left|right",
    "<vertical>": "top|bottom",
    "<percentage>": "(?:[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+))%",
    "<scalar>": "(?:\\d+)|(?:[+-]?([0-9]+([.][0-9]*)?|[.][0-9]+))",
    "<text-align>": "left|right|center",
    "<text-style>": "bold|italic|underline|strikethrough",
    "<overflow>": "auto|hidden|scroll|visible",
    "<display>": "block|none",
    "<box-sizing>": "border-box|content-box",
    "<layout>": "grid|horizontal|vertical",
    "<visibility>": "hidden|visible",
    "<name>": '".*?"',
    "<integer>": "\\d+",
    "<number>": "\\d+\\.\\d+",
}

# Dictionary to store compiled regex patterns for style validation
styles_regex = {}


# Function to compile regex patterns for styles validation
def setup_styles_regex():
    for tag, pattern in styles.items():
        replaced = re.sub(
            "<([^>]+)>",
            lambda x: values[x.group()].pattern if isinstance(values[x.group()], re.Pattern) else values[x.group()],
            pattern,
        )
        flags = re.IGNORECASE if "<color>" in pattern else 0
        styles_regex[tag] = re.compile(replaced, flags)


# Function to validate CSS selector
def validate_selector(selector) -> bool:
    if re.fullmatch(
            r"(\*|([.#]?[\w-]+(\.[\w-]+)*)(\s*(,|>|[\w\s]+)\s*([.#]?[\w-]+(\.[\w-]+)*))*)((:\w+(\([^)]*\))?)*)",
            selector):
        logging.debug(f"Valid selector: {selector}")
        return True
    else:
        logging.warning(f"Invalid selector: {selector}")
        return False


# Function to validate CSS declarations
def validate_declarations(declarations):
    valid = False
    rules = [rule.strip() for rule in declarations.strip().split(';') if rule.strip()]
    for rule in rules:
        prop, value = [item.strip() for item in rule.split(':', 1)]
        if prop in styles_regex:
            pattern = styles_regex[prop]
            if pattern.fullmatch(value):
                logging.debug(f"  Valid: {prop}: {value}")
                valid = True
            else:
                logging.warning(f"  Invalid: {prop}: {value}")
        else:
            logging.warning(f"  Unknown property: {prop}")
    return valid


# Function to split CSS into blocks
def split_css_into_blocks(css):
    css_blocks = []

    # Remove comments
    comment_pattern = re.compile(r'/\*[\s\S]*?\*/|//.*$', re.MULTILINE)
    css = comment_pattern.sub('', css)

    # Match variable declarations
    var_pattern = re.compile(r'\$[\w-]+\s*:\s*[^;]+(?:;|$)')
    variables = var_pattern.findall(css)

    # Process variable declarations
    for var in variables:
        var = re.sub(r'\s*;$', '', var)
        var = re.sub(r"\s+", ' ', var)
        css_blocks.append({'type': 'variable', 'definition': var.strip()})
        logging.debug(f"Valid variable: {var}")
        css = var_pattern.sub('', css, 1)

    # Match selectors and their rules
    selector_pattern = re.compile(r'[\w\s.,#&\[\]()^=:$*>\-]+(?:::?[\w-]+(?:\(.*?\))?)?\s*{[^{}]*}', re.DOTALL)
    selectors = selector_pattern.findall(css)

    for selector in selectors:
        selector_parts = re.split(r'\s*{\s*', selector.strip())
        selector_name = selector_parts[0].strip()
        rules = re.split(r'\s*;\s*', selector_parts[1].rstrip('}').strip())
        rules = [rule for rule in rules if rule]  # Filter out empty elements

        css_blocks.append({
            'type': 'rule',
            'selector': selector_name,
            'rules': rules
        })

    return css_blocks


# Function to validate CSS
def validate_css(css):
    valid_css_parts = []
    variables = {}

    blocks = split_css_into_blocks(css)

    # Process and validate CSS blocks
    for block in blocks:

        if block['type'] == 'variable':
            definition = block['definition']
            name, value = [item.strip() for item in definition.split(':', 1)]
            variables[name] = value
            valid_css_parts.append(definition + ";")

        elif block['type'] == 'rule':
            selector = block['selector']
            valid_selector = validate_selector(selector)

            if not valid_selector:
                continue

            rules = block['rules']
            valid_declarations = []
            for declaration in rules:
                if ':' not in declaration:
                    continue

                prop, value = [item.strip() for item in declaration.split(':', 1)]

                value_with_vars = None

                # Handle variable usage
                if value.startswith('$'):
                    variable_name = value.split()[0]
                    value_with_vars = variable_name  # keep the variables unexpanded for reconstruction
                    if variable_name in variables:
                        value = value.replace(variable_name, variables[variable_name])
                    else:
                        logging.warning(f"Undefined variable: {variable_name}")

                is_important = False
                if value.endswith("!important"):
                    is_important = True
                    value = value[:-11].strip()

                if prop in styles_regex:
                    pattern = styles_regex[prop]
                    if pattern.fullmatch(value):
                        logging.debug(f"Valid: {prop}: {value}")
                        if value_with_vars is not None:
                            value = value_with_vars
                        valid_declarations.append(f'{prop}:{value}{" !important" if is_important == True else ""};')
                    else:
                        logging.warning(f"Invalid: {prop}: {value}")
                else:
                    logging.warning(f"Unknown property: {prop}")

            rebuilt_declarations = ''
            if selector:
                rebuilt_declarations = f'{selector} {{'

            for valid_declaration in valid_declarations:
                rebuilt_declarations += " " + valid_declaration

            if selector:
                rebuilt_declarations += ' }'

            if len(rebuilt_declarations):
                valid_css_parts.append(rebuilt_declarations)

    return '\n'.join(valid_css_parts)


# Initialize the regex patterns for style validation
setup_styles_regex()
