"""Shared access to the crate's emitted schema and semantic metadata."""

import json

import raptor_schema


def resolve(node, root):
    if "$ref" in node:
        return root["definitions"][node["$ref"].rsplit("/", 1)[-1]]
    return node


def nonnull(node):
    if "anyOf" in node:
        return next((part for part in node["anyOf"] if part.get("type") != "null"), node)
    return node


def empty(node, root):
    node = resolve(node, root)
    types = node.get("type", [])
    if (types == "null" or (isinstance(types, list) and "null" in types)) or any(
        p.get("type") == "null" for p in node.get("anyOf", [])
    ):
        return None
    if "properties" in node:
        return {key: empty(value, root) for key, value in node["properties"].items()}
    return [] if node.get("type") == "array" else ""


def schemas():
    return json.loads(raptor_schema.json_schema())


def roles(node, root):
    return resolve(node, root).get("x-raptor-roles", {})
