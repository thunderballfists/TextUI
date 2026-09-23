"""The sole adapter between documents and Textual's native TCSS machinery."""
from __future__ import annotations

from dataclasses import dataclass, replace
from io import StringIO
import re

from rich.console import Console
from textual.app import App
from textual.color import Color
from textual.css.stylesheet import Stylesheet, StylesheetParseError
from textual.css.tokenize import tokenize_declarations
from textual.widget import Widget

from .errors import DocumentStyleError, SourceLocation
from .nodes import StyleBlock


@dataclass(frozen=True, slots=True)
class GradientBackground:
    """A parsed TCSS linear gradient that can be rendered by a bar surface."""

    selector: str
    angle: float
    colors: tuple[Color, ...]

    def renderable(self):
        """Create the native renderable with evenly distributed color stops."""
        from textual.renderables.gradient import LinearGradient

        step = 1 / (len(self.colors) - 1)
        return LinearGradient(self.angle, tuple((index * step, color) for index, color in enumerate(self.colors)))


_CSS_RULE = re.compile(r"(?P<selectors>[^{}]+)(?P<rule>\{(?P<declarations>[^{}]*)\})", re.DOTALL)
_LINEAR_GRADIENT = re.compile(
    r"(?P<property>\bbackground\s*:\s*)"
    r"linear-gradient\(\s*"
    r"(?P<angle>[+-]?(?:\d+(?:\.\d*)?|\.\d+))deg\s*,\s*"
    r"(?P<colors>[^()]+?)\s*\)"
    r"(?P<terminator>\s*;?)",
    re.IGNORECASE,
)
_LINEAR_GRADIENT_START = re.compile(r"\bbackground\s*:\s*linear-gradient\s*\(", re.IGNORECASE)


def _split_selectors(selectors: str) -> tuple[str, ...]:
    """Split a CSS selector list without treating functional selectors as commas."""
    result: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(selectors):
        if character in "([":
            depth += 1
        elif character in ")]":
            depth = max(depth - 1, 0)
        elif character == "," and depth == 0:
            selector = selectors[start:index].strip()
            if selector:
                result.append(selector)
            start = index + 1
    selector = selectors[start:].strip()
    if selector:
        result.append(selector)
    return tuple(result)


def _gradient_backgrounds(block: StyleBlock) -> tuple[StyleBlock, tuple[GradientBackground, ...]]:
    """Replace supported gradient declarations before Textual parses the TCSS."""
    gradients: list[GradientBackground] = []

    def replace_rule(rule_match: re.Match[str]) -> str:
        selectors = rule_match.group("selectors")
        declarations = rule_match.group("declarations")

        def replace_gradient(gradient_match: re.Match[str]) -> str:
            raw_colors = tuple(color.strip() for color in gradient_match.group("colors").split(","))
            if len(raw_colors) < 2 or any(not color for color in raw_colors):
                raise DocumentStyleError(
                    "linear-gradient() requires at least two literal colors",
                    location=block.location,
                )
            try:
                colors = tuple(Color.parse(color) for color in raw_colors)
            except Exception as error:
                raise DocumentStyleError(
                    "linear-gradient() colors must be literal Textual colors",
                    location=block.location,
                ) from error
            for selector in _split_selectors(selectors):
                gradients.append(GradientBackground(selector, float(gradient_match.group("angle")), colors))
            return f"{gradient_match.group('property')}transparent{gradient_match.group('terminator')}"

        cleaned = _LINEAR_GRADIENT.sub(replace_gradient, declarations)
        if _LINEAR_GRADIENT_START.search(cleaned):
            raise DocumentStyleError(
                "linear-gradient() requires an angle in degrees followed by literal colors",
                location=block.location,
            )
        return f"{selectors}{rule_match.group('rule')[0]}{cleaned}}}"

    content = _CSS_RULE.sub(replace_rule, block.content)
    return replace(block, content=content), tuple(gradients)


def prepare_gradient_backgrounds(blocks: tuple[StyleBlock, ...]) -> tuple[tuple[StyleBlock, ...], tuple[GradientBackground, ...]]:
    """Preprocess bar gradient declarations while leaving ordinary TCSS unchanged."""
    prepared: list[StyleBlock] = []
    gradients: list[GradientBackground] = []
    for block in blocks:
        cleaned, extracted = _gradient_backgrounds(block)
        prepared.append(cleaned)
        gradients.extend(extracted)
    return tuple(prepared), tuple(gradients)


def _style_error(error: Exception, location: SourceLocation, *, inline: bool = False) -> DocumentStyleError:
    """Retain native diagnostics and map CSS lines, never decoded XML columns."""
    relative = None
    if isinstance(error, StylesheetParseError):
        for rule in error.errors.rules:
            if rule.errors:
                token = rule.errors[0][0]
                relative = (token.referenced_by or token).location
                break
    else:
        token = getattr(error, 'token', None)
        relative = getattr(getattr(token, 'referenced_by', None) or token, 'location', None)
        if relative is None and getattr(error, 'start', None) is not None:
            # TokenError.start is one-based; Token.location is zero-based.
            relative = tuple(coordinate - 1 for coordinate in error.start)
    stream = StringIO()
    console = Console(file=stream, width=100, color_system=None)
    console.print(error if hasattr(error, '__rich__') else str(error))
    details = stream.getvalue().strip()
    if relative is not None and not inline:
        line, column = relative
        details = f'CSS line {line + 1}, column {column + 1}: {details}'
        location = SourceLocation(location.source, location.line + line if location.line is not None else None, tag=location.tag)
    return DocumentStyleError(details, location=location, attribute='style' if inline else None)


def prepare_styles(app: App, blocks: tuple[StyleBlock, ...]) -> Stylesheet:
    """Parse all document sources on a copy; the host remains untouched."""
    staged = app.stylesheet.copy()
    for block in blocks:
        staged.add_source(block.content, read_from=(block.location.source, f'textui.style[{block.index}]'))
        try:
            staged.parse()
        except Exception as error:
            raise _style_error(error, block.location) from error
    return staged


def prepare_styles_from(
    stylesheet: Stylesheet,
    blocks: tuple[StyleBlock, ...],
    *,
    replace: tuple[StyleBlock, ...] = (),
) -> Stylesheet:
    """Replace selected document sources while retaining all other stylesheet sources."""
    staged = stylesheet.copy()
    active = {
        (block.location.source, f'textui.style[{block.index}]'): block
        for block in blocks
    }
    replaced = {
        (block.location.source, f'textui.style[{block.index}]')
        for block in replace
    }
    for block in replace:
        key = (block.location.source, f'textui.style[{block.index}]')
        replacement = active.get(key)
        staged.add_source(replacement.content if replacement is not None else '', read_from=key)
    for block in blocks:
        key = (block.location.source, f'textui.style[{block.index}]')
        if key not in replaced:
            staged.add_source(block.content, read_from=key)
    try:
        staged.parse()
    except Exception as error:
        location = blocks[0].location if blocks else replace[0].location
        raise _style_error(error, location) from error
    return staged


def apply_inline(widget: Widget, declarations: str, location: SourceLocation) -> None:
    """Use native tokenization and set_styles, with an explicit variable boundary."""
    try:
        for token in tokenize_declarations(declarations, (location.source, 'inline style')):
            if token.name == 'variable_ref':
                raise ValueError('Inline style variable references are not supported; use a <style> block or host TCSS')
        widget.set_styles(declarations)
    except Exception as error:
        raise _style_error(error, location, inline=True) from error


def commit_styles(app: App, staged: Stylesheet) -> None:
    """Install only after the entire native tree has been constructed."""
    app.stylesheet = staged
