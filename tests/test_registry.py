from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

import textui


def test_public_registry_api_is_available():
    assert hasattr(textui, "ComponentRegistry"), "The new registry API is missing"
    assert hasattr(textui, "ComponentSpec"), "The component specification API is missing"


def test_registry_rejects_duplicate_and_reserved_component_names():
    registry = textui.ComponentRegistry()
    spec = textui.ComponentSpec(tag="thing", factory=lambda context: None)
    registry.register(spec)

    with pytest.raises(textui.RegistryError):
        registry.register(spec)
    with pytest.raises(textui.RegistryError):
        registry.register(textui.ComponentSpec(tag="style", factory=lambda context: None))
    with pytest.raises(textui.RegistryError):
        registry.register(textui.ComponentSpec(tag="bad_name", factory=lambda context: None))


def test_registry_reserves_common_and_event_directive_names():
    registry = textui.ComponentRegistry()

    with pytest.raises(textui.RegistryError):
        registry.register(
            textui.ComponentSpec(
                tag="thing", factory=lambda context: None, attributes={"id": textui.AttributeSpec()}
            )
        )
    with pytest.raises(textui.RegistryError):
        registry.register(
            textui.ComponentSpec(
                tag="other", factory=lambda context: None, events={"on-change": textui.EventSpec(object, lambda event: event)}
            )
        )


def test_registry_snapshot_and_spec_mappings_are_immutable_copies():
    attributes = {"choice": textui.AttributeSpec(default="first")}
    events = {"changed": textui.EventSpec(object, lambda event: event)}
    spec = textui.ComponentSpec(
        tag="thing", factory=lambda context: None, attributes=attributes, events=events
    )
    registry = textui.ComponentRegistry()
    registry.register(spec)
    attributes["later"] = textui.AttributeSpec()
    events["later"] = textui.EventSpec(object, lambda event: event)

    snapshot = registry.snapshot()
    registry.register(textui.ComponentSpec(tag="other", factory=lambda context: None))

    assert tuple(snapshot) == ("thing",)
    assert tuple(spec.attributes) == ("choice",)
    assert tuple(spec.events) == ("changed",)
    with pytest.raises(TypeError):
        spec.attributes["new"] = textui.AttributeSpec()
    with pytest.raises(FrozenInstanceError):
        spec.tag = "other"


def test_attribute_defaults_are_isolated_for_each_conversion():
    spec = textui.AttributeSpec(default=[])

    first = spec.value_or_default()
    second = spec.value_or_default()
    first.append("changed")

    assert second == []
    assert first is not second


@pytest.mark.parametrize(
    ("converter", "value", "expected"),
    [
        (textui.boolean, "true", True),
        (textui.boolean, "false", False),
        (textui.integer(), "17", 17),
        (textui.enum("one", "two"), "two", "two"),
    ],
)
def test_converters_return_strict_typed_values(converter, value, expected):
    assert converter(value) == expected


@pytest.mark.parametrize(
    ("converter", "value"),
    [
        (textui.boolean, "False"),
        (textui.integer(), "1.0"),
        (textui.integer(minimum=1), "0"),
        (textui.enum("one", "two"), "three"),
    ],
)
def test_converters_reject_values_outside_their_domains(converter, value):
    with pytest.raises(ValueError):
        converter(value)
