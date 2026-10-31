"""Guard the schema ownership boundary, including nested record property names."""

import ast
import json
import re

import raptor_schema
from corpus_support import ROOT


def test_scripts_own_no_schema_literals():
    schemas = json.loads(raptor_schema.json_schema())
    forbidden = set(schemas)
    for schema in schemas.values():
        for field in schema["x-raptor-fields"]:
            forbidden.update(
                value for value in (field["name"], field["label"], field["section"]) if value
            )
        for node in [schema, *schema["definitions"].values()]:
            forbidden.update(node.get("properties", {}))
            forbidden.update(node.get("enum", []))
        forbidden.update(schema["x-raptor-kinds"])
    forbidden = {value.casefold() for value in forbidden}
    metadata_receivers = {"field", "metadata", "member"}
    for path in (ROOT / "scripts").glob("*.py"):
        tree = ast.parse(path.read_text())
        parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            parent = parents.get(node)
            if isinstance(parent, ast.Subscript) and isinstance(parent.value, ast.Name):
                if parent.value.id in metadata_receivers:
                    continue  # Exported field-metadata API keys, never record property indexing.
            assert node.value.casefold() not in forbidden, (path, node.lineno, node.value)

    for path in (ROOT / "templates").glob("*.j2"):
        body = path.read_text().split("---", 2)[-1]
        for value in forbidden:
            pattern = rf"(?<![A-Za-z0-9_]){re.escape(value)}(?![A-Za-z0-9_])"
            assert not re.search(pattern, body, re.IGNORECASE), (path, value)


def test_crate_source_has_no_forbidden_input_panics_or_markdown_policy():
    forbidden = re.compile(r"rustfmt::skip|unwrap\(\)|expect\(|panic!|unreachable!|todo!")
    for path in (ROOT / "crates/raptor-schema/src").glob("*.rs"):
        source = path.read_text()
        assert not forbidden.search(source), path
        assert not re.search(r"\]\(|\*\*|- \[", source), path
        if path.name != "accept.rs":
            assert "serde_json::Value" not in source, path
