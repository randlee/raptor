"""Pin interpreter coverage to the Rust-owned metadata protocol.

Consumed tags are derived from AST comparisons, including local aliases, rather
than copied into a supported-tag list. These exported tags deliberately use
schema-generic paths rather than a dedicated tag comparison:

Not consumed shapes Text: strings use JSON Schema type and source reconstruction.
Not consumed shapes Date: scalar references select the Rust scalar validator.
Not consumed shapes Version: scalar references select the Rust scalar validator.
Not consumed shapes Status: JSON Schema enum choices select canonical values.
Not consumed shapes Id: scalar references select the Rust scalar validator.
Not consumed shapes TextList: generic array items are text without object roles.
Not consumed shapes Group: collection and caption roles select group rendering.
Not consumed roles header_label: Header level selects source metadata labels.
Not consumed roles item_label: Item level selects source metadata labels.
Not consumed roles section_label: Label level and enclosing section select labels.
Not consumed roles section_prose: Section level and content roles select source prose.
Not consumed roles group: collection roles select group rendering and parsing.
"""

import copy
import json
import re

import pytest
import raptor_schema
from corpus_support import ROOT
from protocol_scan_support import assert_agreement
from schema_scan_support import check_source, check_template


def inputs():
    definitions = json.loads(raptor_schema.json_schema())
    protocols = [schema["x-raptor-protocol"] for schema in definitions.values()]
    assert all(protocol == protocols[0] for protocol in protocols)
    sources = [path.read_text() for path in (ROOT / "scripts").glob("*.py")]
    return definitions, protocols[0], sources


def documented_generic_paths():
    declarations = re.findall(r"^Not consumed (\w+) (\w+): (.+)$", __doc__, re.MULTILINE)
    result = {}
    for category, tag, reason in declarations:
        assert reason.strip()
        result.setdefault(category, {})[tag] = reason
    return result


def test_actual_dispatch_tags_agree_with_rust_protocol_in_both_directions():
    _, protocol, sources = inputs()
    assert_agreement(sources, protocol, documented_generic_paths())


@pytest.mark.parametrize(
    "source",
    [
        'record["rationale"]',
        'record["name"]',
        'field["requirement_statement"]',
        'table = "requirements"',
        'status = "Active"',
        'pattern = r"REQ-[A-Z]{2,5}-\\d{4}"',
        'pattern = r"[A-Z]+-[A-Z]{2,5}-\\d{4}"',
        'token.partition("-")',
        'role.startswith("heading_")',
    ],
)
def test_seeded_schema_and_id_policy_violations_fail_normal_scan(source):
    definitions, _, _ = inputs()
    with pytest.raises(AssertionError):
        check_source(source, definitions)


@pytest.mark.parametrize(
    "seed",
    [
        'def bad(field):\n    return field["shape"] == "UnexportedShape"',
        'def bad(semantic):\n    return semantic["unexported_role"]',
        'SUPPORTED = ["Checklist"]',
        'TREE_KEY = "heading_id"',
    ],
)
def test_seeded_protocol_drift_or_hand_lists_fail_dispatch_agreement(seed):
    _, protocol, sources = inputs()
    with pytest.raises(AssertionError):
        assert_agreement([*sources, seed], protocol, documented_generic_paths())


def test_exported_but_unhandled_protocol_tag_fails_coverage():
    _, protocol, sources = inputs()
    changed = copy.deepcopy(protocol)
    changed["levels"].append("UnconsumedLevel")
    with pytest.raises(AssertionError):
        assert_agreement(sources, changed, documented_generic_paths())


def test_seeded_template_schema_literal_fails_normal_template_scan():
    definitions, _, _ = inputs()
    with pytest.raises(AssertionError):
        check_template("### Requirement Statement", definitions)


def test_changed_heading_partition_requires_matching_python_key_use():
    _, protocol, sources = inputs()
    changed = copy.deepcopy(protocol)
    changed["heading_roles"]["unexpected"] = changed["roles"][-1]
    with pytest.raises(AssertionError):
        assert_agreement(sources, changed, documented_generic_paths())
