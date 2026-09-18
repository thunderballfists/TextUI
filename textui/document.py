"""Immutable document definitions produced by :class:`DocumentLoader`."""
from __future__ import annotations

from dataclasses import dataclass

from .nodes import ElementNode, StyleBlock


@dataclass(frozen=True, slots=True)
class Document:
    nodes: tuple[ElementNode, ...]
    styles: tuple[StyleBlock, ...]
    source_name: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "styles", tuple(self.styles))
