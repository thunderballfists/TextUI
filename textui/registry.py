"""Typed component definitions and the explicit component registry."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from textual.widget import Widget
from .errors import RegistryError, SourceLocation


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
    def convert(value: str) -> int:
        if not value or (value[0] in "+-" and len(value) == 1) or not value.lstrip("+-").isdigit():
            raise ValueError(f"expected a base-10 integer; got {value!r}")
        result = int(value, 10)
        if minimum is not None and result < minimum:
            raise ValueError(f"expected an integer >= {minimum}; got {value!r}")
        if maximum is not None and result > maximum:
            raise ValueError(f"expected an integer <= {maximum}; got {value!r}")
        return result
    return convert


def enum(*values: str) -> Callable[[str], str]:
    allowed = tuple(values)
    def convert(value: str) -> str:
        if value not in allowed:
            raise ValueError(f"expected one of {', '.join(repr(choice) for choice in allowed)}; got {value!r}")
        return value
    return convert


@dataclass(frozen=True, slots=True)
class AttributeSpec:
    converter: Callable[[str], Any] = str
    required: bool = False
    default: Any = UNSET
    def __post_init__(self) -> None:
        if not callable(self.converter):
            raise RegistryError("attribute converter must be callable")
        if self.required and self.default is not UNSET:
            raise RegistryError("a required attribute cannot have a default")
    def value_or_default(self) -> Any:
        if self.default is UNSET:
            return UNSET
        return deepcopy(self.default)


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
    def __post_init__(self) -> None:
        if not callable(self.factory):
            raise RegistryError("component factory must be callable")
        if self.text_policy not in {"none", "text"}:
            raise RegistryError("text_policy must be 'none' or 'text'")
        if self.child_policy not in {"none", "widgets"}:
            raise RegistryError("child_policy must be 'none' or 'widgets'")
        attributes, events = _frozen_mapping(self.attributes), _frozen_mapping(self.events)
        if any(not isinstance(spec, AttributeSpec) for spec in attributes.values()):
            raise RegistryError("component attributes must contain AttributeSpec values")
        if any(not isinstance(spec, EventSpec) for spec in events.values()):
            raise RegistryError("component events must contain EventSpec values")
        object.__setattr__(self, "attributes", attributes)
        object.__setattr__(self, "events", events)


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
    _RESERVED_TAGS = frozenset({"ui", "style", "script"})
    _COMMON_ATTRIBUTES = frozenset({"id", "class", "style", "disabled"})
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


def _is_kebab_name(name: str) -> bool:
    import re

    return bool(re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", name))
