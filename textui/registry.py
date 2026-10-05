"""Typed component definitions and the explicit component registry."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from textual.widget import Widget
from .errors import RegistryError, SourceLocation
from .metadata import Bool, Enum, Int, Text, ValueType, Custom
from .content import Children


class _Unset:
    def __repr__(self) -> str:
        return "UNSET"


UNSET = _Unset()


def _frozen_mapping(mapping: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(mapping))


def boolean(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError(f"expected true or false; got {value!r}")


def integer(*, minimum: int | None = None, maximum: int | None = None) -> Callable[[str], int]:
    return Int(minimum, maximum)


def enum(*values: str) -> Callable[[str], str]:
    return Enum(*values)


@dataclass(frozen=True, slots=True)
class AttributeSpec:
    converter: Callable[[str], Any] = str
    required: bool = False
    default: Any = UNSET
    doc: str = ""
    value_type: ValueType | None = None
    def __post_init__(self) -> None:
        if not callable(self.converter):
            raise RegistryError("attribute converter must be callable")
        if self.required and self.default is not UNSET:
            raise RegistryError("a required attribute cannot have a default")
        if self.value_type is not None and not isinstance(self.value_type, ValueType):
            raise RegistryError("attribute value_type must be a ValueType")
    def value_or_default(self) -> Any:
        if self.default is UNSET:
            return UNSET
        return deepcopy(self.default)

    def describe(self) -> dict[str, object]:
        value_type = self.value_type
        if value_type is None:
            if isinstance(self.converter, ValueType):
                value_type = self.converter
            elif self.converter is str:
                value_type = Text()
            elif self.converter is boolean:
                value_type = Bool()
            else:
                value_type = Custom(self.converter)
        result: dict[str, object] = {"type": value_type.describe(), "required": self.required}
        if self.default is not UNSET:
            result["default"] = self.value_or_default()
        if self.doc:
            result["doc"] = self.doc
        return result


@dataclass(frozen=True, slots=True)
class EventSpec:
    message_type: type
    source_widget: Callable[[Any], Widget]
    def __post_init__(self) -> None:
        if not isinstance(self.message_type, type):
            raise RegistryError("event message_type must be a type")
        if not callable(self.source_widget):
            raise RegistryError("event source_widget must be callable")


@dataclass(frozen=True, slots=True)
class ComponentSpec:
    tag: str
    factory: Callable[["BuildContext"], Widget]
    attributes: Mapping[str, AttributeSpec] = field(default_factory=dict)
    text_policy: str = "none"
    child_policy: str = "none"
    events: Mapping[str, EventSpec] = field(default_factory=dict)
    content: Children | None = None
    def __post_init__(self) -> None:
        if not callable(self.factory):
            raise RegistryError("component factory must be callable")
        if self.text_policy not in {"none", "text", "verbatim"}:
            raise RegistryError("text_policy must be 'none', 'text', or 'verbatim'")
        if self.child_policy not in {"none", "widgets"}:
            raise RegistryError("child_policy must be 'none' or 'widgets'")
        attributes, events = _frozen_mapping(self.attributes), _frozen_mapping(self.events)
        if any(not isinstance(spec, AttributeSpec) for spec in attributes.values()):
            raise RegistryError("component attributes must contain AttributeSpec values")
        if any(not isinstance(spec, EventSpec) for spec in events.values()):
            raise RegistryError("component events must contain EventSpec values")
        object.__setattr__(self, "attributes", attributes)
        object.__setattr__(self, "events", events)
        if self.content is not None:
            if not isinstance(self.content, Children):
                raise RegistryError("component content must be Children")
            if self.content.policy != self.child_policy:
                raise RegistryError("content policy must match child_policy")

    def describe(self) -> dict[str, object]:
        from .widgets.metadata import content_for
        content = content_for(self)
        return {"tag": self.tag, "attributes": {name: spec.describe() for name, spec in self.attributes.items()},
                "text_policy": self.text_policy, "content": content.describe(),
                "events": {name: {"message_type": f"{spec.message_type.__module__}.{spec.message_type.__qualname__}"}
                           for name, spec in self.events.items()}}


@dataclass(frozen=True, slots=True)
class BuildContext:
    attributes: Mapping[str, Any]
    text: str | None
    children: tuple[Widget, ...]
    location: SourceLocation
    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", _frozen_mapping(self.attributes))
        object.__setattr__(self, "children", tuple(self.children))


class ComponentRegistry:
    _RESERVED_TAGS = frozenset({"ui", "style", "script", "include"})
    _COMMON_ATTRIBUTES = frozenset({"id", "class", "style", "disabled", "autofocus"})
    def __init__(self) -> None:
        self._specifications: dict[str, ComponentSpec] = {}

    def register(self, spec: ComponentSpec) -> None:
        if not isinstance(spec, ComponentSpec):
            raise RegistryError("registry entries must be ComponentSpec instances")
        if not _is_kebab_name(spec.tag):
            raise RegistryError(f"invalid component tag {spec.tag!r}")
        if spec.tag in self._RESERVED_TAGS:
            raise RegistryError(f"component tag {spec.tag!r} is reserved")
        if spec.tag in self._specifications:
            raise RegistryError(f"component tag {spec.tag!r} is already registered")
        for name in spec.attributes:
            if not _is_kebab_name(name):
                raise RegistryError(f"invalid component directive {name!r}")
            if name in self._COMMON_ATTRIBUTES or name.startswith("on-"):
                raise RegistryError(f"component attribute {name!r} is reserved")
        for name in spec.events:
            if not _is_kebab_name(name):
                raise RegistryError(f"invalid component directive {name!r}")
            if name.startswith("on-"):
                raise RegistryError(f"event name {name!r} must omit the 'on-' prefix")
        self._specifications[spec.tag] = spec

    def get(self, tag: str) -> ComponentSpec | None:
        return self._specifications.get(tag)

    def snapshot(self) -> Mapping[str, ComponentSpec]:
        return MappingProxyType(dict(self._specifications))

    def describe(self) -> dict[str, object]:
        """Inspect registrations without constructing widgets or invoking converters."""
        from .widgets.metadata import DOCUMENT_RULES
        common = {"id": AttributeSpec(), "class": AttributeSpec(default=()), "style": AttributeSpec(),
                  "disabled": AttributeSpec(boolean, default=False), "autofocus": AttributeSpec(boolean, default=False)}
        return {"components": [spec.describe() for spec in self._specifications.values()],
                "common_attributes": {name: spec.describe() for name, spec in common.items()},
                "document_rules": [rule.describe() for rule in DOCUMENT_RULES]}


def _is_kebab_name(name: str) -> bool:
    import re

    return bool(re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", name))
