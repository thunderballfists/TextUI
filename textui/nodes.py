"""Immutable parsed document records."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any
from .errors import SourceLocation
from .registry import ComponentSpec

def _freeze(mapping: Mapping[str, Any]) -> Mapping[str, Any]: return MappingProxyType(dict(mapping))

@dataclass(frozen=True, slots=True)
class ElementNode:
    spec: ComponentSpec
    attributes: Mapping[str, Any]
    common: Mapping[str, Any]
    text: str | None
    children: tuple["ElementNode", ...]
    events: Mapping[str, str]
    location: SourceLocation
    private_id: bool = False
    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", _freeze(self.attributes))
        object.__setattr__(self, "common", _freeze(self.common))
        object.__setattr__(self, "children", tuple(self.children))
        object.__setattr__(self, "events", _freeze(self.events))

@dataclass(frozen=True, slots=True)
class StyleBlock:
    content: str
    location: SourceLocation
    index: int
