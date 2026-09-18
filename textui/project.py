"""Discovery of a local TextUI project without executing linked Python."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lxml import etree

from .document import Document
from .errors import DocumentLoadError, DocumentValidationError, SourceLocation
from .loader import DocumentLoader
from .nodes import StyleBlock
from .registry import ComponentRegistry


@dataclass(slots=True)
class ProjectSource:
    path: Path
    root: etree._Element
    sources: dict[etree._Element, str]
    styles: tuple[StyleBlock, ...]
    scripts: tuple[Path, ...]

    @classmethod
    def discover(cls, path: str | Path) -> ProjectSource:
        entry = Path(path).resolve()
        parser = DocumentLoader()
        sources: dict[etree._Element, str] = {}
        styles: list[StyleBlock] = []
        scripts: list[Path] = []

        def read(path: Path, location: SourceLocation | None = None) -> str:
            try:
                return path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as error:
                raise DocumentLoadError(f"could not read {path}", location=location or SourceLocation(str(path), None)) from error

        def parse(path: Path) -> etree._Element:
            root = parser._parse(read(path), str(path))
            parser._reject_parser_bypasses(root, str(path))
            location = parser._location(root, str(path))
            if root.tag != "ui" or root.nsmap:
                raise DocumentValidationError("expected a <ui> root without namespaces", location=location)
            if root.attrib:
                raise DocumentValidationError("root accepts no attributes", location=location, attribute=next(iter(root.attrib)))
            parser._reject_nonwhitespace(root.text, location, "root text is not allowed")
            for element in root.iter():
                sources[element] = str(path)
            return root

        def directive(element: etree._Element, owner: Path) -> tuple[Path, SourceLocation]:
            location = parser._location(element, str(owner))
            if set(element.attrib) != {"src"} or not element.get("src"):
                raise DocumentValidationError(f"{element.tag} requires exactly one nonempty src", location=location)
            if element.text and element.text.strip() or len(element):
                raise DocumentValidationError(f"{element.tag} cannot contain content", location=location)
            value = element.get("src")
            if "://" in value or value.startswith("//"):
                raise DocumentValidationError("resource must be a local file", location=location, attribute="src", value=value)
            return (owner.parent / value).resolve(), location

        def expand(parent: etree._Element, owner: Path, stack: tuple[Path, ...], *, entry_root: bool = False) -> None:
            index = 0
            while index < len(parent):
                child = parent[index]
                if isinstance(child, etree._Comment):
                    parser._reject_nonwhitespace(child.tail, parser._location(parent, str(owner)), "non-whitespace tail text is not allowed")
                    index += 1
                    continue
                location = parser._location(child, str(owner))
                if not isinstance(child.tag, str):
                    raise DocumentValidationError("processing instructions are not allowed", location=location)
                parser._reject_nonwhitespace(child.tail, location, "non-whitespace tail text is not allowed")
                if child.tag == "include":
                    target, _ = directive(child, owner)
                    if target in stack:
                        chain = " -> ".join(str(item) for item in (*stack, target))
                        raise DocumentValidationError(f"include cycle: {chain}", location=location)
                    included = parse(target)
                    expand(included, target, (*stack, target))
                    replacements = list(included)
                    parent.remove(child)
                    for offset, replacement in enumerate(replacements):
                        parent.insert(index + offset, replacement)
                    index += len(replacements)
                    continue
                if child.tag in {"style", "script"}:
                    if not entry_root:
                        raise DocumentValidationError(f"{child.tag} is allowed only in the entry root", location=location)
                    if child.tag == "style" and not child.attrib:
                        styles.append(parser._style(child, location, len(styles)))
                    else:
                        target, _ = directive(child, owner)
                        content = read(target, location)
                        if child.tag == "style":
                            styles.append(StyleBlock(content, SourceLocation(str(target), 1, tag="style"), len(styles)))
                        else:
                            scripts.append(target)
                else:
                    expand(child, owner, stack)
                index += 1

        root = parse(entry)
        expand(root, entry, (entry,), entry_root=True)
        return cls(entry, root, sources, tuple(styles), tuple(scripts))

    def lower(self, registry: ComponentRegistry) -> Document:
        loader = DocumentLoader(registry)
        identifiers: set[str] = set()
        nodes = tuple(
            loader._node(child, self.sources.get(child, str(self.path)), identifiers, self.sources)
            for child in self.root
            if isinstance(child.tag, str) and child.tag not in {"style", "script"}
        )
        return Document(nodes, self.styles, str(self.path))
