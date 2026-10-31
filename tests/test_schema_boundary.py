"""Guard the schema ownership boundary, including nested record property names."""

import json
import re

import raptor_schema
from corpus_support import ROOT


def test_scripts_own_no_schema_literals():
    from schema_scan_support import check_source, check_template

    schemas = json.loads(raptor_schema.json_schema())
    for path in (ROOT / "scripts").glob("*.py"):
        check_source(path.read_text(), schemas)
    for path in (ROOT / "templates").glob("*.j2"):
        check_template(path.read_text(), schemas)


def test_crate_source_has_no_forbidden_input_panics_or_markdown_policy():
    forbidden = re.compile(r"rustfmt::skip|unwrap\(\)|expect\(|panic!|unreachable!|todo!")
    for path in (ROOT / "crates/raptor-schema/src").rglob("*.rs"):
        source = path.read_text()
        assert not forbidden.search(source), path
        assert not re.search(r"\]\(|\*\*|- \[", source), path
        relative = path.relative_to(ROOT / "crates/raptor-schema/src").as_posix()
        if relative not in {"accept.rs", "emit.rs", "boundary.rs", "error.rs"}:
            assert "serde_json::Value" not in source, path
