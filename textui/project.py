"""Discovery of a local TextUI project without executing linked Python."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import re

from lxml import etree

from .document import Document
from .errors import DocumentLoadError, DocumentValidationError, SourceLocation
from .loader import DocumentLoader
from .nodes import StyleBlock
from .registry import ComponentRegistry
from .widgets.navigation import validate_navigation_targets
from .widgets.structure import validate_control_structure


_KEBAB = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
_PLACEHOLDER = re.compile(r"\{([a-z][a-z0-9]*(?:-[a-z0-9]+)*)\}")
_COMMON = frozenset({"id", "class", "style", "disabled"})


@dataclass(slots=True, frozen=True)
class _ComponentTemplate:
    path: Path
    props: dict[str, str | None]
    root: etree._Element
    imports: dict[str, _ComponentTemplate]


@dataclass(slots=True)
class ProjectSource:
    path: Path
    root: etree._Element
    sources: dict[etree._Element, str]
    styles: tuple[StyleBlock, ...]
    scripts: tuple[Path, ...]
    components: dict[str, _ComponentTemplate]

    @classmethod
    def discover(cls, path: str | Path) -> ProjectSource:
        entry = Path(path).resolve()
        parser = DocumentLoader()
        sources: dict[etree._Element, str] = {}
        styles: list[StyleBlock] = []
        scripts: list[Path] = []
        templates: dict[Path, _ComponentTemplate] = {}

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

        def directive(element: etree._Element, owner: Path, *, attributes: set[str] = {"src"}) -> tuple[Path, SourceLocation]:
            location = parser._location(element, str(owner))
            if set(element.attrib) != attributes or not element.get("src"):
                raise DocumentValidationError(f"{element.tag} requires required attributes", location=location)
            if element.text and element.text.strip() or len(element):
                raise DocumentValidationError(f"{element.tag} cannot contain content", location=location)
            value = element.get("src")
            if "://" in value or value.startswith("//"):
                raise DocumentValidationError("resource must be a local file", location=location, attribute="src", value=value)
            return (owner.parent / value).resolve(), location

        def reject_tail(element: etree._Element, owner: Path) -> None:
            parser._reject_nonwhitespace(element.tail, parser._location(element, str(owner)), "non-whitespace tail text is not allowed")

        def parse_template(path: Path, stack: tuple[Path, ...]) -> _ComponentTemplate:
            if path in stack:
                chain = " -> ".join(str(item) for item in (*stack, path))
                raise DocumentValidationError("component import cycle: " + chain, location=SourceLocation(str(path), None))
            if path in templates:
                return templates[path]
            root = parser._parse(read(path), str(path))
            parser._reject_parser_bypasses(root, str(path))
            location = parser._location(root, str(path))
            if root.tag != "component" or root.nsmap:
                raise DocumentValidationError("expected a <component> root without namespaces", location=location)
            if root.attrib:
                raise DocumentValidationError("component root accepts no attributes", location=location, attribute=next(iter(root.attrib)))
            parser._reject_nonwhitespace(root.text, location, "component root text is not allowed")
            for element in root.iter():
                sources[element] = str(path)

            imports: dict[str, _ComponentTemplate] = {}
            props: dict[str, str | None] = {}
            widget_roots: list[etree._Element] = []
            saw_props = False
            for child in root:
                if isinstance(child, etree._Comment):
                    reject_tail(child, path)
                    continue
                if not isinstance(child.tag, str):
                    raise DocumentValidationError("processing instructions are not allowed", location=location)
                reject_tail(child, path)
                child_location = parser._location(child, str(path))
                if child.tag == "component":
                    target, _ = directive(child, path, attributes={"src", "as"})
                    alias = child.get("as")
                    if not alias or not _KEBAB.fullmatch(alias):
                        raise DocumentValidationError("component alias must be lowercase kebab-case", location=child_location, attribute="as", value=alias)
                    if alias in imports:
                        raise DocumentValidationError("duplicate component alias", location=child_location, attribute="as", value=alias)
                    imports[alias] = parse_template(target, (*stack, path))
                elif child.tag == "props":
                    if saw_props or widget_roots or child.attrib:
                        raise DocumentValidationError("props must appear once before the widget root", location=child_location)
                    saw_props = True
                    parser._reject_nonwhitespace(child.text, child_location, "props text is not allowed")
                    for prop in child:
                        if isinstance(prop, etree._Comment):
                            reject_tail(prop, path)
                            continue
                        prop_location = parser._location(prop, str(path))
                        if prop.tag != "prop" or prop.text and prop.text.strip() or len(prop):
                            raise DocumentValidationError("props may contain only empty <prop> declarations", location=prop_location)
                        reject_tail(prop, path)
                        if not set(prop.attrib).issubset({"name", "required", "default"}) or not prop.get("name"):
                            raise DocumentValidationError("prop requires a name", location=prop_location)
                        name = prop.get("name")
                        if not _KEBAB.fullmatch(name) or name in props:
                            raise DocumentValidationError("prop name must be unique lowercase kebab-case", location=prop_location, attribute="name", value=name)
                        required = prop.get("required")
                        if required not in {None, "true", "false"} or required == "true" and "default" in prop.attrib:
                            raise DocumentValidationError("prop required must be true or false and cannot have a default", location=prop_location)
                        props[name] = None if required == "true" else prop.get("default", "")
                elif child.tag in {"style", "script", "include", "slot"}:
                    raise DocumentValidationError(f"{child.tag} is not allowed in a component definition", location=child_location)
                else:
                    widget_roots.append(child)
            if len(widget_roots) != 1:
                raise DocumentValidationError("component requires exactly one widget root", location=location)
            template = _ComponentTemplate(path, props, widget_roots[0], imports)
            templates[path] = template
            return template

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
                if child.tag == "component":
                    if not entry_root:
                        raise DocumentValidationError("component imports are allowed only in the entry root", location=location)
                    index += 1
                    continue
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
                        elif target not in scripts:
                            scripts.append(target)
                else:
                    expand(child, owner, stack)
                index += 1

        root = parse(entry)
        expand(root, entry, (entry,), entry_root=True)
        components: dict[str, _ComponentTemplate] = {}
        for child in root:
            if not isinstance(child.tag, str) or child.tag != "component":
                continue
            location = parser._location(child, str(entry))
            target, _ = directive(child, entry, attributes={"src", "as"})
            alias = child.get("as")
            if not alias or not _KEBAB.fullmatch(alias):
                raise DocumentValidationError("component alias must be lowercase kebab-case", location=location, attribute="as", value=alias)
            if alias in components:
                raise DocumentValidationError("duplicate component alias", location=location, attribute="as", value=alias)
            components[alias] = parse_template(target, ())
        return cls(entry, root, sources, tuple(styles), tuple(scripts), components)

    def lower(self, registry: ComponentRegistry) -> Document:
        loader = DocumentLoader(registry)
        identifiers: set[str] = set()
        private_ids: set[str] = set()
        instance = 0

        def mark_source(element: etree._Element, source: str) -> None:
            for node in element.iter():
                sources[node] = source

        def copy_with_sources(element: etree._Element, default: str) -> etree._Element:
            copy = deepcopy(element)
            for original, copied in zip(element.iter(), copy.iter(), strict=True):
                sources[copied] = sources.get(original, default)
            return copy

        sources = dict(self.sources)

        def substitute(value: str | None, props: dict[str, str], location: SourceLocation) -> str | None:
            if value is None:
                return None
            if "{" in value or "}" in value:
                if re.sub(_PLACEHOLDER, "", value).find("{") >= 0 or re.sub(_PLACEHOLDER, "", value).find("}") >= 0:
                    raise DocumentValidationError("malformed component placeholder", location=location)
                def replace(match: re.Match[str]) -> str:
                    name = match.group(1)
                    if name not in props:
                        raise DocumentValidationError("unknown component property in placeholder", location=location, attribute=name)
                    return props[name]
                return _PLACEHOLDER.sub(replace, value)
            return value

        def expand_element(element: etree._Element, scope: dict[str, _ComponentTemplate], chain: tuple[Path, ...]) -> etree._Element:
            nonlocal instance
            if element.tag not in scope:
                for child in list(element):
                    if isinstance(child.tag, str):
                        replacement = expand_element(child, scope, chain)
                        if replacement is not child:
                            element.replace(child, replacement)
                return element
            template = scope[element.tag]
            if template.path in chain:
                cycle = " -> ".join(str(item) for item in (*chain, template.path))
                raise DocumentValidationError("component expansion cycle: " + cycle, location=loader._location(element, sources.get(element, str(self.path))))
            location = loader._location(element, sources.get(element, str(self.path)))
            props: dict[str, str] = {}
            for name in element.attrib:
                if name not in template.props and name not in _COMMON and not name.startswith("on-"):
                    raise DocumentValidationError("unknown component property", location=location, attribute=name, value=element.get(name))
            for name, default in template.props.items():
                if name in element.attrib:
                    props[name] = element.get(name, "")
                elif default is None:
                    raise DocumentValidationError("required component property is missing", location=location, attribute=name)
                else:
                    props[name] = default
            loader._reject_nonwhitespace(element.text, location, "component call text is not allowed")
            supplied: dict[str | None, list[etree._Element]] = {}
            for child in element:
                loader._reject_nonwhitespace(child.tail, location, "non-whitespace tail text is not allowed")
                if isinstance(child, etree._Comment):
                    continue
                if child.tag == "slot":
                    if set(child.attrib) != {"name"} or not child.get("name"):
                        raise DocumentValidationError("component slot requires one nonempty name", location=location)
                    loader._reject_nonwhitespace(child.text, location, "slot text is not allowed")
                    name = child.get("name")
                    if name in supplied:
                        raise DocumentValidationError("duplicate component slot", location=location, attribute="name", value=name)
                    supplied[name] = list(child)
                else:
                    supplied.setdefault(None, []).append(child)
            instance += 1
            prefix = f"__component_{instance}_"
            result = deepcopy(template.root)
            mark_source(result, str(template.path))
            private_id_map: dict[str, str] = {}
            for node in result.iter():
                node.text = substitute(node.text, props, loader._location(node, str(template.path)))
                for name, value in list(node.attrib.items()):
                    node.set(name, substitute(value, props, loader._location(node, str(template.path))) or "")
                if node.get("id"):
                    original_id = node.get("id")
                    private_id = prefix + original_id
                    node.set("id", private_id)
                    private_ids.add(private_id)
                    private_id_map[original_id] = private_id
            for node in result.iter():
                for attribute in {"initial", "target"}:
                    if node.get(attribute) in private_id_map:
                        node.set(attribute, private_id_map[node.get(attribute)])
            defined_slots: set[str | None] = set()
            for slot in list(result.iter("slot")):
                slot_location = loader._location(slot, str(template.path))
                loader._reject_nonwhitespace(slot.text, slot_location, "slot text is not allowed")
                name = slot.get("name")
                if not set(slot.attrib).issubset({"name"}) or name in defined_slots:
                    raise DocumentValidationError("component slot declarations must have unique optional names", location=slot_location)
                defined_slots.add(name)
                parent = slot.getparent()
                index = parent.index(slot)
                if name in supplied:
                    replacement = supplied.pop(name)
                    replacement_scope = scope
                else:
                    replacement = list(slot)
                    replacement_scope = template.imports
                parent.remove(slot)
                for offset, child in enumerate(replacement):
                    copy = copy_with_sources(child, str(self.path))
                    copy = expand_element(copy, replacement_scope, chain)
                    parent.insert(index + offset, copy)
            if supplied:
                name = next(iter(supplied))
                raise DocumentValidationError("unknown component slot", location=location, attribute="name", value=name)
            for name, value in element.attrib.items():
                if name == "id":
                    result.set(name, value)
                elif name == "class":
                    result.set(name, " ".join(filter(None, [result.get(name, ""), value])))
                elif name in {"style", "disabled"} or name.startswith("on-"):
                    result.set(name, value)
            return expand_element(result, template.imports, (*chain, template.path))

        roots = []
        for child in self.root:
            if not isinstance(child.tag, str) or child.tag in {"style", "script", "component"}:
                continue
            root = copy_with_sources(child, str(self.path))
            roots.append(expand_element(root, self.components, ()))
        nodes = tuple(
            loader._node(child, sources.get(child, str(self.path)), identifiers, sources, private_ids)
            for child in roots
        )
        validate_navigation_targets(nodes)
        validate_control_structure(nodes)
        return Document(nodes, self.styles, str(self.path))
