"""Strict ownership and ID-policy scans used by the normal schema boundary tests."""

import ast
import re


def vocabulary(schemas):
    forbidden = set(schemas)
    metadata_keys = set()
    for schema in schemas.values():
        for field in schema["x-raptor-fields"]:
            metadata_keys.update(field)
            forbidden.update(
                value for value in (field["name"], field["label"], field["section"]) if value
            )
        for node in [schema, *schema["definitions"].values()]:
            forbidden.update(node.get("properties", {}))
            forbidden.update(node.get("enum", []))
        forbidden.update(schema["x-raptor-kinds"])
    return {value.casefold() for value in forbidden}, metadata_keys


def check_source(source, schemas):
    forbidden, metadata_keys = vocabulary(schemas)
    tree = ast.parse(source)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"partition", "split", "rsplit"} and node.args:
                argument = node.args[0]
                assert not (isinstance(argument, ast.Constant) and argument.value == "-"), (
                    "ID structure parsing belongs to Rust",
                    node.lineno,
                )
            if node.func.attr == "startswith" and node.args:
                argument = node.args[0]
                assert not (isinstance(argument, ast.Constant) and argument.value == "heading_"), (
                    "Heading role partition must come from Rust",
                    node.lineno,
                )
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        value = node.value
        assert not re.search(r"(?:ADR|REQ|NFR)-", value, re.IGNORECASE), (
            "ID prefix policy",
            node.lineno,
        )
        assert not (
            re.search(r"\[[Aa]-[Zz]\]", value)
            and "-" in value
            and (r"\d" in value or "[0-9]" in value)
        ), ("ID grammar", node.lineno)
        parent = parents.get(node)
        if isinstance(parent, ast.Subscript) and isinstance(parent.value, ast.Name):
            if parent.value.id in {"field", "metadata", "member"} and value in metadata_keys:
                continue
        assert value.casefold() not in forbidden, ("Canonical schema literal", node.lineno, value)
    return tree


def check_template(source, schemas):
    forbidden, _ = vocabulary(schemas)
    body = source.split("---", 2)[-1]
    for value in forbidden:
        pattern = rf"(?<![A-Za-z0-9_]){re.escape(value)}(?![A-Za-z0-9_])"
        assert not re.search(pattern, body, re.IGNORECASE), ("Canonical template literal", value)
