"""The sole adapter between documents and Textual's native TCSS machinery."""
from __future__ import annotations

from io import StringIO

from rich.console import Console
from textual.app import App
from textual.css.stylesheet import Stylesheet, StylesheetParseError
from textual.css.tokenize import tokenize_declarations
from textual.widget import Widget

from .errors import DocumentStyleError, SourceLocation
from .nodes import StyleBlock


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
