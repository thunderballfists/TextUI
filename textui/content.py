"""Immutable, ordered content constraints for registry inspection and loading."""
from __future__ import annotations

from collections.abc import Callable, Sequence as ChildSequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .errors import DocumentValidationError

if TYPE_CHECKING:
    from .nodes import ElementNode
    from textual.widget import Widget


@dataclass(frozen=True, slots=True)
class ElementRef:
    tag: str
    factory: object | None = None

    def matches(self, node: ElementNode) -> bool:
        return node.spec.factory is self.factory if self.factory is not None else node.spec.tag == self.tag

    def describe(self) -> dict[str, object]:
        return {"tag": self.tag, "match": "factory" if self.factory is not None else "tag"}


class Rule:
    __slots__ = ()

    def validate(self, node: ElementNode, parent: ElementNode | None) -> None:
        raise NotImplementedError

    def describe(self) -> dict[str, object]:
        raise NotImplementedError


def _fail(node: ElementNode, message: str, attribute: str | None = None) -> None:
    raise DocumentValidationError(message, location=node.location, attribute=attribute)


@dataclass(frozen=True, slots=True)
class Parent(Rule):
    allowed: tuple[ElementRef, ...] = ()
    message: str = "invalid parent"
    root_only: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed", tuple(self.allowed))

    def validate(self, node: ElementNode, parent: ElementNode | None) -> None:
        valid = parent is None if self.root_only else parent is not None and any(ref.matches(parent) for ref in self.allowed)
        if not valid:
            _fail(node, self.message)

    def describe(self) -> dict[str, object]:
        return {"rule": "parent", "root_only": self.root_only,
                "allowed": [ref.describe() for ref in self.allowed], "message": self.message, "phase": "document"}


@dataclass(frozen=True, slots=True)
class RequireCommon(Rule):
    attribute: str
    message: str

    def validate(self, node: ElementNode, parent: ElementNode | None) -> None:
        if node.common[self.attribute] is None:
            _fail(node, self.message, self.attribute)

    def describe(self) -> dict[str, object]:
        return {"rule": "require-common", "attribute": self.attribute, "message": self.message, "phase": "document"}


@dataclass(frozen=True, slots=True)
class Needs(Rule):
    source: str
    target: str
    attribute: str
    message: str

    def validate(self, node: ElementNode, parent: ElementNode | None) -> None:
        if self.source in node.attributes and self.target not in node.attributes:
            _fail(node, self.message, self.attribute)

    def describe(self) -> dict[str, object]:
        return {"rule": "needs", "source": self.source, "target": self.target,
                "attribute": self.attribute, "message": self.message, "phase": "document"}


@dataclass(frozen=True, slots=True)
class Only(Rule):
    allowed: tuple[ElementRef, ...]
    message: str = "invalid children"

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed", tuple(self.allowed))

    def validate(self, node: ElementNode, parent: ElementNode | None) -> None:
        if any(not any(ref.matches(child) for ref in self.allowed) for child in node.children):
            _fail(node, self.message)

    def describe(self) -> dict[str, object]:
        return {"rule": "only", "allowed": [ref.describe() for ref in self.allowed],
                "message": self.message, "phase": "document"}


@dataclass(frozen=True, slots=True)
class Count(Rule):
    minimum: int = 0
    maximum: int | None = None
    message: str = "invalid child count"

    def validate(self, node: ElementNode, parent: ElementNode | None) -> None:
        count = len(node.children)
        if count < self.minimum or self.maximum is not None and count > self.maximum:
            _fail(node, self.message)

    def describe(self) -> dict[str, object]:
        return {"rule": "count", "minimum": self.minimum, "maximum": self.maximum,
                "message": self.message, "phase": "document"}


@dataclass(frozen=True, slots=True)
class Sequence(Rule):
    groups: tuple[ElementRef, ...]
    message: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "groups", tuple(self.groups))

    def validate(self, node: ElementNode, parent: ElementNode | None) -> None:
        previous = -1
        for child in node.children:
            index = next((i for i, ref in enumerate(self.groups) if ref.matches(child)), -1)
            if index < previous:
                _fail(node, self.message)
            previous = index

    def describe(self) -> dict[str, object]:
        return {"rule": "sequence", "groups": [ref.describe() for ref in self.groups],
                "message": self.message, "phase": "document"}


@dataclass(frozen=True, slots=True)
class UniqueSlots(Rule):
    message: str

    def validate(self, node: ElementNode, parent: ElementNode | None) -> None:
        tags = [child.spec.tag for child in node.children]
        if len(tags) != len(set(tags)):
            _fail(node, self.message)

    def describe(self) -> dict[str, object]:
        return {"rule": "unique-slots", "message": self.message, "phase": "document"}


@dataclass(frozen=True, slots=True)
class ForbidCommon(Rule):
    message: str
    events: bool = False

    def validate(self, node: ElementNode, parent: ElementNode | None) -> None:
        if (node.common["id"] is not None or node.common["classes"] or node.common["style"] is not None
                or node.common["disabled"] or self.events and node.events):
            _fail(node, self.message)

    def describe(self) -> dict[str, object]:
        return {"rule": "forbid-common", "attributes": ["id", "class", "style", "disabled"],
                "events": self.events, "message": self.message, "phase": "document"}


@dataclass(frozen=True, slots=True)
class NamedCheck(Rule):
    name: str
    doc: str
    check: Callable[[ElementNode, ElementNode | None], None] | None = None
    phase: str = "document"

    def validate(self, node: ElementNode, parent: ElementNode | None) -> None:
        if self.phase == "document" and self.check is not None:
            self.check(node, parent)

    def describe(self) -> dict[str, object]:
        return {"rule": "named", "name": self.name, "doc": self.doc, "phase": self.phase}


@dataclass(frozen=True, slots=True)
class NativeChildren(Rule):
    """Construction constraints match actual widget instances, including subclasses."""
    widget_type: type[Widget]
    message: str
    minimum: int = 0
    maximum: int | None = None

    def validate(self, node: ElementNode, parent: ElementNode | None) -> None:
        pass  # Native children do not exist at document-validation time.

    def validate_build(self, children: ChildSequence[Widget]) -> None:
        if (len(children) < self.minimum or self.maximum is not None and len(children) > self.maximum
                or any(not isinstance(child, self.widget_type) for child in children)):
            raise ValueError(self.message)

    def describe(self) -> dict[str, object]:
        return {"rule": "native-children", "widget_type": f"{self.widget_type.__module__}.{self.widget_type.__qualname__}",
                "minimum": self.minimum, "maximum": self.maximum, "message": self.message, "phase": "build"}


@dataclass(frozen=True, slots=True)
class Children:
    rules: tuple[Rule, ...] = ()
    policy: str = "widgets"

    def __post_init__(self) -> None:
        object.__setattr__(self, "rules", tuple(self.rules))

    def validate(self, node: ElementNode, parent: ElementNode | None) -> None:
        for rule in self.rules:
            rule.validate(node, parent)

    def describe(self) -> dict[str, object]:
        return {"policy": self.policy, "rules": [rule.describe() for rule in self.rules]}
