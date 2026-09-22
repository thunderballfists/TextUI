"""Strict XML parsing and lowering into immutable TextUI documents."""
from __future__ import annotations

from pathlib import Path
import re
from collections.abc import Mapping
from typing import Any

from lxml import etree
from textual.dom import check_identifiers

from .document import Document
from .errors import DocumentLoadError, DocumentSyntaxError, DocumentValidationError, SourceLocation
from .nodes import ElementNode, StyleBlock
from .presets import style_preset
from .registry import AttributeSpec, ComponentRegistry, UNSET, boolean
from .widgets.builtin_widgets import default_component_registry
from .widgets.display_controls import build_range
from .widgets.navigation import validate_navigation_targets
from .widgets.structure import validate_control_structure

_KEBAB = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
_ACTION = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_COMMON = frozenset({"id", "class", "style", "disabled"})


class DocumentLoader:
    def __init__(self, registry: ComponentRegistry | None = None) -> None:
        self._registry = (registry or default_component_registry()).snapshot()

    def from_file(self, path: str | Path) -> Document:
        source = str(Path(path).resolve())
        try:
            markup = Path(path).read_text(encoding="utf-8")
        except OSError as error:
            location = SourceLocation(source, None)
            exception = DocumentLoadError("could not read document", location=location)
            raise exception from error
        return self.from_string(markup, source_name=source)

    def from_string(self, markup: str, source_name: str = "<string>") -> Document:
        if not isinstance(markup, str):
            raise TypeError("markup must be a string")
        if re.search(r"<\?xml[^>]*encoding\s*=\s*['\"](?!utf-?8['\"])[^'\"]+['\"]", markup, re.I):
            raise DocumentSyntaxError("XML declaration must specify UTF-8", location=SourceLocation(source_name, 1))
        root = self._parse(markup, source_name)
        self._reject_parser_bypasses(root, source_name)
        root_location = self._location(root, source_name)
        if root.tag != "ui" or root.nsmap:
            raise DocumentValidationError("expected a <ui> root without namespaces", location=root_location)
        if root.attrib:
            attribute = next(iter(root.attrib))
            raise DocumentValidationError("root accepts no attributes", location=root_location, attribute=attribute)
        self._reject_nonwhitespace(root.text, root_location, "root text is not allowed")
        identifiers: set[str] = set()
        nodes: list[ElementNode] = []
        styles: list[StyleBlock] = []
        for child in root:
            if isinstance(child, etree._Comment):
                self._reject_nonwhitespace(child.tail, root_location, "non-whitespace tail text is not allowed")
                continue
            if not isinstance(child.tag, str):
                raise DocumentSyntaxError("processing instructions are not allowed", location=root_location)
            location = self._location(child, source_name)
            if child.tag == "style":
                styles.append(self._style(child, location, len(styles)))
            else:
                nodes.append(self._node(child, source_name, identifiers))
            self._reject_nonwhitespace(child.tail, root_location, "non-whitespace tail text is not allowed")
        validate_navigation_targets(nodes)
        validate_control_structure(nodes)
        return Document(tuple(nodes), tuple(styles), source_name)

    def _parse(self, markup: str, source_name: str) -> etree._Element:
        parser = etree.XMLParser(recover=False, resolve_entities=False, load_dtd=False, no_network=True, huge_tree=False, remove_comments=False, remove_pis=False, strip_cdata=False)
        try:
            return etree.fromstring(markup.encode("utf-8"), parser=parser)
        except etree.XMLSyntaxError as error:
            line, column = error.position
            exception = DocumentSyntaxError(str(error), location=SourceLocation(source_name, line, column))
            raise exception from error

    def _reject_parser_bypasses(self, root: etree._Element, source_name: str) -> None:
        tree = root.getroottree()
        if tree.docinfo.doctype:
            raise DocumentSyntaxError("DTD declarations are not allowed", location=SourceLocation(source_name, 1))
        sibling = root.getprevious()
        while sibling is not None:
            if isinstance(sibling, etree._ProcessingInstruction):
                raise DocumentSyntaxError("processing instructions are not allowed", location=self._location(sibling, source_name))
            sibling = sibling.getprevious()
        sibling = root.getnext()
        while sibling is not None:
            if isinstance(sibling, etree._ProcessingInstruction):
                raise DocumentSyntaxError("processing instructions are not allowed", location=self._location(sibling, source_name))
            sibling = sibling.getnext()
        for node in tree.iter():
            if isinstance(node, etree._ProcessingInstruction):
                raise DocumentSyntaxError("processing instructions are not allowed", location=self._location(node, source_name))
            if isinstance(node, etree._Entity):
                raise DocumentSyntaxError("entity references are not allowed", location=self._location(node, source_name))
            if isinstance(node.tag, str) and (node.tag.startswith("{") or any(key.startswith("{") for key in node.attrib)):
                raise DocumentValidationError("namespaces are not allowed", location=self._location(node, source_name))

    def _style(self, element: etree._Element, location: SourceLocation, index: int) -> StyleBlock:
        if "preset" in element.attrib:
            if set(element.attrib) != {"preset"}:
                attribute = next(name for name in element.attrib if name != "preset")
                raise DocumentValidationError("style preset accepts only the preset attribute", location=location, attribute=attribute)
            has_comment_tail = any(
                comment.tail and comment.tail.strip()
                for comment in element
                if isinstance(comment, etree._Comment)
            )
            if (
                any(not isinstance(child, etree._Comment) for child in element)
                or (element.text and element.text.strip())
                or has_comment_tail
            ):
                raise DocumentValidationError("style preset cannot contain content", location=location)
            try:
                content = style_preset(element.attrib["preset"])
            except ValueError as error:
                raise DocumentValidationError(str(error), location=location, attribute="preset", value=element.attrib["preset"]) from error
            return StyleBlock(content, location, index, preset=element.attrib["preset"])
        if element.attrib:
            attribute = next(iter(element.attrib))
            raise DocumentValidationError("style accepts no attributes", location=location, attribute=attribute)
        if any(not isinstance(child, etree._Comment) for child in element):
            raise DocumentValidationError("style cannot contain elements", location=location)
        content = "".join(
            [element.text or "", *(comment.tail or "" for comment in element)]
        )
        return StyleBlock(content, location, index)

    def _node(self, element: etree._Element, source_name: str, identifiers: set[str], sources: Mapping[etree._Element, str] | None = None, private_ids: set[str] | None = None) -> ElementNode:
        source_name = sources.get(element, source_name) if sources is not None else source_name
        location = self._location(element, source_name)
        if not _KEBAB.fullmatch(element.tag):
            raise DocumentValidationError("element name must be lowercase kebab-case", location=location)
        spec = self._registry.get(element.tag)
        if spec is None:
            raise DocumentValidationError(f"unknown component {element.tag!r}", location=location)
        if spec.tag in {"option", "column", "row", "cell", "tree-node"}:
            for name in element.attrib:
                if name in _COMMON:
                    raise DocumentValidationError(
                        f"{spec.tag} accepts no common widget attributes",
                        location=location, attribute=name,
                    )
        attributes: dict[str, Any] = {}
        common: dict[str, Any] = {"id": None, "classes": (), "style": None, "disabled": False}
        events: dict[str, str] = {}
        for name, raw in element.attrib.items():
            if not _KEBAB.fullmatch(name):
                raise DocumentValidationError("attribute name must be lowercase kebab-case", location=location, attribute=name, value=raw)
            if name in _COMMON:
                self._common(common, identifiers, name, raw, location)
            elif name.startswith("on-"):
                event_name = name.removeprefix("on-")
                if event_name not in spec.events:
                    raise DocumentValidationError(f"unknown event {event_name!r}", location=location, attribute=name, value=raw)
                if not _ACTION.fullmatch(raw):
                    raise DocumentValidationError("action must be a nonempty Python identifier", location=location, attribute=name, value=raw)
                events[event_name] = raw
            elif name not in spec.attributes:
                raise DocumentValidationError("unknown attribute", location=location, attribute=name, value=raw)
            else:
                attributes[name] = self._convert(spec.attributes[name], raw, location, name)
        for name, attribute_spec in spec.attributes.items():
            if name in attributes:
                continue
            if attribute_spec.required:
                raise DocumentValidationError("required attribute is missing", location=location, attribute=name)
            default = attribute_spec.value_or_default()
            if default is not UNSET:
                attributes[name] = default
        if spec.factory is build_range and "value" not in attributes:
            attributes["value"] = attributes["min"]
        children = tuple(self._children(element, source_name, identifiers, spec.child_policy, location, sources, private_ids))
        if spec.text_policy in {"text", "verbatim"}:
            if any(not isinstance(child, etree._Comment) for child in element):
                raise DocumentValidationError("text component cannot contain child elements", location=location)
            text = self._normal_text(element) if spec.text_policy == "text" else "".join(element.itertext())
        else:
            self._reject_nonwhitespace(element.text, location, "text is not allowed")
            text = None
        return ElementNode(spec, attributes, common, text, children, events, location, common["id"] in (private_ids or set()))

    def _children(self, element: etree._Element, source_name: str, identifiers: set[str], policy: str, location: SourceLocation, sources: Mapping[etree._Element, str] | None = None, private_ids: set[str] | None = None):
        elements = [child for child in element if not isinstance(child, etree._Comment)]
        if policy == "none":
            if elements:
                raise DocumentValidationError("component cannot contain child elements", location=location)
            return
        for child in element:
            if isinstance(child, etree._Comment):
                self._reject_nonwhitespace(child.tail, location, "non-whitespace tail text is not allowed")
                continue
            yield self._node(child, source_name, identifiers, sources, private_ids)
            self._reject_nonwhitespace(child.tail, location, "non-whitespace tail text is not allowed")

    def _common(self, common: dict[str, Any], identifiers: set[str], name: str, raw: str, location: SourceLocation) -> None:
        if name == "id":
            if not raw:
                raise DocumentValidationError("id cannot be empty", location=location, attribute=name, value=raw)
            try:
                check_identifiers("id", raw)
            except Exception as error:
                raise DocumentValidationError(str(error), location=location, attribute=name, value=raw) from error
            if raw in identifiers:
                raise DocumentValidationError("duplicate id", location=location, attribute=name, value=raw)
            identifiers.add(raw)
            common["id"] = raw
        elif name == "class":
            classes = tuple(dict.fromkeys(raw.split()))
            try:
                check_identifiers("class name", *classes)
            except Exception as error:
                raise DocumentValidationError(str(error), location=location, attribute=name, value=raw) from error
            common["classes"] = classes
        elif name == "disabled":
            common["disabled"] = self._convert(
                AttributeSpec(boolean), raw, location, name
            )
        else:
            common["style"] = raw

    def _convert(self, attribute_spec: Any, raw: str, location: SourceLocation, name: str) -> Any:
        try:
            return attribute_spec.converter(raw)
        except ValueError as error:
            raise DocumentValidationError(str(error), location=location, attribute=name, value=raw) from error

    @staticmethod
    def _normal_text(element: etree._Element) -> str:
        return " ".join("".join(element.itertext()).split())

    @staticmethod
    def _reject_nonwhitespace(value: str | None, location: SourceLocation, message: str) -> None:
        if value and value.strip():
            raise DocumentValidationError(message, location=location)

    @staticmethod
    def _location(element: etree._Element, source_name: str) -> SourceLocation:
        tag = element.tag if isinstance(element.tag, str) and not element.tag.startswith("{") else None
        return SourceLocation(source_name, element.sourceline, tag=tag)
