"""Immutable, inspectable attribute types; conversion remains explicit."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite
import re
from typing import Any


class ValueType(ABC):
    __slots__ = ()

    def __call__(self, value: str) -> Any:
        return self.convert(value)

    @abstractmethod
    def convert(self, value: str) -> Any:
        """Convert one literal attribute value."""

    @abstractmethod
    def describe(self) -> dict[str, object]:
        """Return a fresh description without running conversion."""


@dataclass(frozen=True, slots=True)
class Text(ValueType):
    def convert(self, value: str) -> str:
        return value

    def describe(self) -> dict[str, object]:
        return {"type": "string"}


@dataclass(frozen=True, slots=True)
class Bool(ValueType):
    def convert(self, value: str) -> bool:
        if value == "true":
            return True
        if value == "false":
            return False
        raise ValueError(f"expected true or false; got {value!r}")

    def describe(self) -> dict[str, object]:
        return {"type": "boolean", "values": ["true", "false"]}


@dataclass(frozen=True, slots=True)
class Int(ValueType):
    minimum: int | None = None
    maximum: int | None = None

    def convert(self, value: str) -> int:
        if not value or (value[0] in "+-" and len(value) == 1) or not value.lstrip("+-").isdigit():
            raise ValueError(f"expected a base-10 integer; got {value!r}")
        result = int(value, 10)
        if self.minimum is not None and result < self.minimum:
            raise ValueError(f"expected an integer >= {self.minimum}; got {value!r}")
        if self.maximum is not None and result > self.maximum:
            raise ValueError(f"expected an integer <= {self.maximum}; got {value!r}")
        return result

    def describe(self) -> dict[str, object]:
        result: dict[str, object] = {"type": "integer"}
        if self.minimum is not None:
            result["minimum"] = self.minimum
        if self.maximum is not None:
            result["maximum"] = self.maximum
        return result


@dataclass(frozen=True, slots=True, init=False)
class Enum(ValueType):
    values: tuple[str, ...]

    def __init__(self, *values: str) -> None:
        object.__setattr__(self, "values", tuple(values))

    def convert(self, value: str) -> str:
        if value not in self.values:
            raise ValueError(f"expected one of {', '.join(repr(choice) for choice in self.values)}; got {value!r}")
        return value

    def describe(self) -> dict[str, object]:
        return {"type": "enum", "values": list(self.values)}


@dataclass(frozen=True, slots=True)
class Pattern(ValueType):
    pattern: str

    def convert(self, value: str) -> str:
        if re.fullmatch(self.pattern, value) is None:
            raise ValueError(f"expected pattern {self.pattern!r}; got {value!r}")
        return value

    def describe(self) -> dict[str, object]:
        return {"type": "string", "pattern": self.pattern}


@dataclass(frozen=True, slots=True)
class IdRef(ValueType):
    """Describe reference scope; contextual checks retain their existing stage."""
    among: str = "document"

    def convert(self, value: str) -> str:
        return value

    def describe(self) -> dict[str, object]:
        return {"type": "string", "reference": {"among": self.among}}


@dataclass(frozen=True, slots=True)
class Number(ValueType):
    positive: bool = False

    def convert(self, value: str) -> float:
        try:
            result = float(value)
        except ValueError as error:
            raise ValueError(f"expected a finite number; got {value!r}") from error
        if not isfinite(result) or (result <= 0 if self.positive else result < 0):
            condition = "positive finite" if self.positive else "nonnegative finite"
            raise ValueError(f"expected a {condition} number; got {value!r}")
        return result

    def describe(self) -> dict[str, object]:
        return {"type": "number", "minimum": 0, "exclusive_minimum": self.positive, "finite": True}


@dataclass(frozen=True, slots=True)
class ValidatedText(ValueType):
    """A named string domain whose existing validator remains authoritative."""
    validation: str
    converter: Callable[[str], str]

    def convert(self, value: str) -> str:
        return self.converter(value)

    def describe(self) -> dict[str, object]:
        return {"type": "string", "validation": self.validation}


@dataclass(frozen=True, slots=True)
class Custom(ValueType):
    converter: Callable[[str], Any]

    def convert(self, value: str) -> Any:
        return self.converter(value)

    def describe(self) -> dict[str, object]:
        return {"type": "custom"}
