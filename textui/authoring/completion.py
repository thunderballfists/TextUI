"""Completion-only formats for VS Code and JetBrains HTML tooling."""
from __future__ import annotations

import json


def type_label(value_type: dict) -> str:
    if "values" in value_type:
        return " / ".join(f"`{value}`" for value in value_type["values"])
    qualifiers = []
    for key in ("minimum", "maximum", "validation", "pattern", "reference"):
        if key in value_type:
            qualifiers.append(f"{key}={json.dumps(value_type[key], ensure_ascii=False)}")
    return value_type["type"] + ("; " + ", ".join(qualifiers) if qualifiers else "")


def attribute_description(attribute: dict) -> str:
    result = type_label(attribute["type"])
    if attribute["required"]:
        result += "; required"
    if "default" in attribute:
        result += "; default=" + json.dumps(attribute["default"], ensure_ascii=False)
    if attribute.get("doc"):
        result += ". " + attribute["doc"]
    return result


def attributes_for(component: dict, common: dict) -> dict:
    rules = component["content"]["rules"]
    forbidden = any(rule["rule"] == "forbid-common" for rule in rules)
    attributes = dict({} if forbidden else common)
    attributes.update(component["attributes"])
    for rule in rules:
        if rule["rule"] == "require-common":
            attributes[rule["attribute"]] = {**attributes[rule["attribute"]], "required": True}
    return attributes


def completion_data(description: dict) -> tuple[dict, dict]:
    tags, web_elements = [], []
    for component in description["components"]:
        attrs = []
        for name, attribute in attributes_for(component, description["common_attributes"]).items():
            item = {"name": name, "description": attribute_description(attribute)}
            if "values" in attribute["type"]:
                item["values"] = [{"name": value} for value in attribute["type"]["values"]]
            attrs.append(item)
        attrs.extend({"name": f"on-{name}", "description": f"Python action identifier; {event['message_type']}"}
                     for name, event in component["events"].items())
        text = f"TextUI {component['tag']}; text: {component['text_policy']}; children: {component['content']['policy']}. XML syntax required."
        tags.append({"name": component["tag"], "description": text, "attributes": attrs})
        web_attrs = []
        for attr in attrs:
            item = {"name": attr["name"], "description": attr["description"]}
            item["value"] = {"kind": "plain", "type": "enum" if "values" in attr else "string"}
            if "values" in attr:
                item["value"]["type"] = [value["name"] for value in attr["values"]]
            web_attrs.append(item)
        web_elements.append({"name": component["tag"], "description": text, "attributes": web_attrs})
    return {"version": 1.1, "tags": tags}, {
        "$schema": "https://raw.githubusercontent.com/JetBrains/web-types/master/schema/web-types.json",
        "name": "textui-markup", "version": "0.7.0", "contributions": {"html": {"elements": web_elements}},
    }
