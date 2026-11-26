"""Authoring templates render new REQ, NFR and ADR records that import clean."""

import json
import re
from pathlib import Path

import pytest
import sc_compose as sc
from corpus_support import ROOT, extract, load_run, run
from scripts.schema_json import schemas

FIXTURES = ROOT / "tests/fixtures/authoring"
SAMPLES = {
    "req-new": ("req.json", "requirements"),
    "nfr-new": ("nfr.json", "requirements"),
    "adr-new": ("adr.json", "decisions"),
}
STRICT = sc.ComposePolicy(strict_undeclared_variables=True, unknown_variable_policy="error")

# Every optional section and label of each table, filled with resolvable values.
LINKS = {
    "design_documents": ["[export design](https://example.test/export)"],
    "work_items": ["[issue 12](https://example.test/issues/12)"],
    "external_references": ["[RFC 8259](https://www.rfc-editor.org/rfc/rfc8259)"],
}
REQUIREMENT_FULL = LINKS | {
    "should": ["`smp export` SHOULD print the number of records it wrote."],
    "test_evidence": ["tests/test_export.py"],
    "applies_to": ["the `smp` command-line tool"],
    "does_not_apply_to": ["the `smp` web viewer"],
    "key_considerations": ["Stream records so memory stays flat."],
    "test_types": ["CLI integration test"],
    "architecture_decisions": ["ADR-SMP-0001"],
}
FULL = {
    "req-new": REQUIREMENT_FULL
    | {"requires": ["NFR-SMP-0001"], "requirements": ["NFR-SMP-0001"]},
    "nfr-new": REQUIREMENT_FULL
    | {"requires": ["REQ-SMP-0001"], "requirements": ["REQ-SMP-0001"]},
    "adr-new": LINKS
    | {
        "architecture_decisions": ["ADR-SMP-0001"],
        "background": "Exports were plain text before this decision.",
        "chosen_approach": "Serialize with sorted keys.",
        "key_principles": ["Same records, same bytes."],
        "benefits": ["Stable diffs."],
        "trade_offs": ["No inline comments."],
        "neutral": ["File size is unchanged."],
        "implementation": "The exporter calls the JSON encoder once.",
        "key_components": ["exporter"],
        "integration_points": ["`smp export`"],
        "code_examples": "`json.dumps(records, sort_keys=True, indent=2)`",
        "impact_analysis": "Only the exporter changes.",
        "affected_components": "exporter",
        "performance_impact": "None measured.",
        "security_impact": "None.",
        "maintainability_impact": "One encoder call to maintain.",
    },
}


def sample(template):
    return json.loads((FIXTURES / SAMPLES[template][0]).read_text())


def render(template, variables):
    request = sc.ComposeRequest(
        root=ROOT,
        mode=sc.ComposeMode.file(f"templates/{template}.md.j2"),
        vars_input=variables,
        policy=STRICT,
    )
    return sc.compose_file(request).rendered_text.rstrip() + "\n"


def project(tmp_path: Path, overrides=None) -> Path:
    """Write the three sample records, each with its overrides, into an empty project."""
    root = tmp_path / "project"
    (root / ".raptor").mkdir(parents=True)
    (root / ".raptor/raptor.toml").write_text('repository_id = "urn:test"\n')
    (root / ".raptor/sources.toml").write_text(
        '[[sources]]\nroot = "docs"\ninclude = ["**/*.md"]\nexclude = []\n'
    )
    (root / "docs").mkdir()
    for template in SAMPLES:
        variables = sample(template) | (overrides or {}).get(template, {})
        (root / "docs" / f"{variables['id']}.md").write_text(render(template, variables))
    return root


def imported(root: Path, tmp_path: Path):
    index = tmp_path / "index.json"
    result = extract(root, index, check=False)
    return result, json.loads(index.read_text())


def test_samples_import_with_zero_diagnostics(tmp_path):
    result, index = imported(project(tmp_path), tmp_path)
    assert index["diagnostics"]["issues"] == [], result.stderr
    assert result.returncode == 0
    assert sorted(record["id"] for record in index["requirements"]) == [
        "NFR-SMP-0001",
        "REQ-SMP-0001",
    ]
    assert [record["id"] for record in index["decisions"]] == ["ADR-SMP-0001"]



def test_rendered_records_load_into_sqlite_and_query_back(tmp_path):
    """Render, import, load and read back each kind: the path judge-jev and agents use."""
    root = project(tmp_path)
    index, database = tmp_path / "index.json", tmp_path / "records.sqlite"
    extract(root, index)
    load_run(str(index), str(database))
    stored = json.loads(index.read_text())
    for template, (_, table) in SAMPLES.items():
        identifier = sample(template)["id"]
        result = run("raptor_query.py", "get", identifier, "--db", str(database), check=False)
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stderr == ""
        envelope = json.loads(result.stdout)
        record = next(item for item in stored[table] if item["id"] == identifier)
        kind = template.split("-")[0]
        assert envelope == {"success": True, "data": [{**record, "type": kind}], "error": None}


@pytest.mark.parametrize("template", SAMPLES)
def test_every_schema_section_renders_in_schema_order_and_imports(tmp_path, template):
    table = SAMPLES[template][1]
    fields = schemas()[table]["x-raptor-fields"]
    root = project(tmp_path, {template: FULL[template]})
    text = (root / "docs" / f"{sample(template)['id']}.md").read_text()
    expected = [field["label"] for field in fields if field["level"] == "Section"]
    assert re.findall(r"^### (.+)$", text, re.MULTILINE) == expected
    labels = {field["label"] for field in fields if field["level"] == "Label"}
    assert labels <= set(re.findall(r"^\*\*(.+?):\*\*$", text, re.MULTILINE))
    result, index = imported(root, tmp_path)
    assert index["diagnostics"]["issues"] == [], result.stderr


@pytest.mark.parametrize(
    "template,empty,absent",
    [
        ("req-new", {"related": [], "test_types": []}, ["### Dependencies", "### Test Strategy"]),
        ("nfr-new", {"related": [], "test_types": []}, ["### Dependencies", "### Test Strategy"]),
        (
            "adr-new",
            {"alternatives": [], "requirements": []},
            ["### Alternatives Considered", "### Related Documents"],
        ),
    ],
)
def test_empty_optional_section_is_omitted(tmp_path, template, empty, absent):
    root = project(tmp_path, {template: empty})
    text = (root / "docs" / f"{sample(template)['id']}.md").read_text()
    for heading in absent:
        assert heading not in text
    result, index = imported(root, tmp_path)
    assert index["diagnostics"]["issues"] == [], result.stderr


@pytest.mark.parametrize(
    "template,missing,section",
    [
        ("req-new", {"rationale": ""}, "Rationale"),
        ("nfr-new", {"acceptance_criteria": []}, "Success Criteria"),
        ("adr-new", {"positive": [], "negative": []}, "Consequences"),
    ],
)
def test_missing_required_body_is_reported_by_import(tmp_path, template, missing, section):
    root = project(tmp_path, {template: missing})
    text = (root / "docs" / f"{sample(template)['id']}.md").read_text()
    assert f"### {section}\n" in text
    result, index = imported(root, tmp_path)
    issues = index["diagnostics"]["issues"]
    record = sample(template)["id"]
    assert result.returncode == 1
    assert [
        (issue["rule"], issue["section"]) for issue in issues if issue["rule"] == "MISSING_FIELD"
    ] == [("MISSING_FIELD", section)]
    # The refused record is not imported, so references to it from the other samples dangle.
    others = [issue for issue in issues if issue["rule"] != "MISSING_FIELD"]
    assert {(issue["rule"], issue["value"]) for issue in others} <= {("DANGLING_REFERENCE", record)}


@pytest.mark.parametrize("template", SAMPLES)
def test_unknown_variable_is_refused(template):
    with pytest.raises(sc.ScValidationError):
        render(template, sample(template) | {"mustnot": ["misspelled"]})
