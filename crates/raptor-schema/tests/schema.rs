use raptor_schema::*;
use rusqlite::Connection;
use serde_json::{Value, json};

fn tree() -> Value {
    json!({"path":"records.md","header":{"Status":{"value":"Draft","line":2},"Version":{"value":"1.0.0","line":3},"Created":{"value":"2026-01-01","line":4},"Last Updated":{"value":"2026-01-02","line":5},"Owner":{"value":"Example","line":6}},"records":[{"id":"REQ-FIX-0001","title":"Requirement","line":9,"fields":{"Status":{"value":"Active","line":10}},"sections":[{"name":"Requirement Statement","line":11,"labels":[]},{"name":"Rationale","line":12,"labels":[]},{"name":"Success Criteria","line":13,"labels":[]}]}]})
}
fn only(bound: &Bound, rule: Rule) -> &Diagnostic {
    assert_eq!(bound.diagnostics.len(), 1);
    let diagnostic = &bound.diagnostics[0];
    assert_eq!(diagnostic.rule, rule);
    assert_eq!(
        (diagnostic.message, diagnostic.remedy),
        match rule {
            Rule::MissingId | Rule::MissingField =>
                ("required field is missing", "Add the required field."),
            Rule::BadValue => ("field value is invalid", "Use the documented value format."),
            Rule::UnknownSection => (
                "section is not defined",
                "Remove the section or use an allowed section."
            ),
            Rule::UnknownLabel => (
                "label is not defined",
                "Remove the label or use an allowed label."
            ),
            Rule::DuplicateId => ("duplicate identifier", "Make the identifier unique."),
            Rule::DanglingReference => (
                "reference does not declare a record",
                "Declare the referenced identifier or remove the reference.",
            ),
        }
    );
    diagnostic
}

#[test]
fn fixture_and_emissions_are_valid() {
    let fixture: serde_json::Value =
        serde_json::from_str(include_str!("../../../tests/fixtures/records.json")).unwrap();
    let requirements: Vec<Requirement> =
        serde_json::from_value(fixture["requirements"].clone()).unwrap();
    let decisions: Vec<Decision> = serde_json::from_value(fixture["decisions"].clone()).unwrap();
    assert_eq!(requirements.len() + decisions.len(), 4);
    assert!(field_table("requirements").len() > 9);
    assert_eq!(
        field_table("requirements")
            .into_iter()
            .filter(|field| field.name == "status")
            .map(|field| field.level)
            .collect::<Vec<_>>(),
        [Level::Header, Level::Item]
    );
    for (table, row) in [
        (
            "requirements",
            serde_json::to_value(&requirements[0]).unwrap(),
        ),
        ("decisions", serde_json::to_value(&decisions[0]).unwrap()),
    ] {
        let fields: std::collections::HashSet<_> = field_table(table)
            .into_iter()
            .filter(|field| field.name != "id_range" && field.level != Level::Label)
            .map(|field| field.name.to_owned())
            .collect();
        let names = row.as_object().unwrap().keys().cloned().collect();
        assert_eq!(fields, names);
    }
    let validator = jsonschema::validator_for(&json_schema()).unwrap();
    assert!(validator.validate(&fixture).is_ok());
}

#[test]
fn inventory_reports_each_duplicate() {
    let row = bind_file(&tree()).requirements.remove(0);
    let rows = vec![row.clone(), row];
    let diagnostics = check_inventory(&rows, &[]);
    assert_eq!(diagnostics.len(), 2);
    assert!(diagnostics.iter().all(|diagnostic| {
        diagnostic.rule == Rule::DuplicateId
            && (diagnostic.message, diagnostic.remedy)
                == ("duplicate identifier", "Make the identifier unique.")
    }));
}

#[test]
fn bind_inherits_headers_and_item_status_wins() {
    let bound = bind_file(&tree());
    assert!(bound.diagnostics.is_empty());
    assert_eq!(bound.requirements[0].identity.id.0, "REQ-FIX-0001");
    assert_eq!(bound.requirements[0].lifecycle.status, Status::Active);
}

#[test]
fn missing_id_has_no_row() {
    let mut value = tree();
    value["records"][0].as_object_mut().unwrap().remove("id");
    let bound = bind_file(&value);
    let diagnostic = only(&bound, Rule::MissingId);
    assert_eq!(diagnostic.file, "records.md");
    assert_eq!(diagnostic.line, 9);
    assert_eq!(diagnostic.label, None);
    assert!(bound.requirements.is_empty());
}

#[test]
fn missing_field_has_no_row() {
    let mut value = tree();
    value["header"].as_object_mut().unwrap().remove("Owner");
    let bound = bind_file(&value);
    assert_eq!(
        only(&bound, Rule::MissingField).id.as_ref().unwrap().0,
        "REQ-FIX-0001"
    );
    assert!(bound.requirements.is_empty());
}

#[test]
fn unknown_section_keeps_row() {
    let mut value = tree();
    value["records"][0]["sections"] = json!([{"name":"Requirement Statement","line":11,"labels":[]},{"name":"Rationale","line":12,"labels":[]},{"name":"Success Criteria","line":13,"labels":[]},{"name":"Extra","line":14,"labels":[]}]);
    let bound = bind_file(&value);
    let diagnostic = only(&bound, Rule::UnknownSection);
    assert_eq!(
        (
            diagnostic.line,
            diagnostic.label.as_deref(),
            diagnostic.allowed.as_ref().unwrap()
        ),
        (
            14,
            Some("Extra"),
            &vec![
                "Requirement Statement".into(),
                "Rationale".into(),
                "Success Criteria".into(),
                "Dependencies".into(),
                "Product Applicability".into(),
                "Implementation Notes".into(),
                "Test Strategy".into(),
                "Related Documents".into()
            ]
        )
    );
    assert_eq!(bound.requirements.len(), 1);
}

#[test]
fn unknown_label_keeps_row() {
    let mut value = tree();
    value["records"][0]["fields"]["Priority"] = json!({"value":"high","line":11});
    let bound = bind_file(&value);
    let diagnostic = only(&bound, Rule::UnknownLabel);
    assert_eq!(diagnostic.line, 11);
    assert_eq!(diagnostic.label.as_deref(), Some("Priority"));
    assert!(
        diagnostic
            .allowed
            .as_ref()
            .unwrap()
            .contains(&"Status".into())
    );
    let summary = summarize(&bound.diagnostics);
    assert_eq!(summary["counts"]["UNKNOWN_LABEL"], 1);
    assert_eq!(summary["groups"][0]["files"]["records.md"], json!([11]));
    assert_eq!(bound.requirements.len(), 1);
}

#[test]
fn bad_value_has_no_row() {
    let mut value = tree();
    value["header"]["Created"]["value"] = json!("2026-02-30");
    let bound = bind_file(&value);
    assert_eq!(only(&bound, Rule::BadValue).line, 9);
    assert!(bound.requirements.is_empty());
}

fn bind_labels(section: &str, labels: &[(&str, &[&str])]) -> Requirement {
    let mut value = tree();
    let sections = value["records"][0]["sections"].as_array_mut().unwrap();
    sections.retain(|s| s["name"] != section);
    let labels: Vec<_> = labels
        .iter()
        .map(|(name, items)| {
            let items: Vec<_> = items
                .iter()
                .map(|text| json!({"text":text,"line":21}))
                .collect();
            json!({"name":name,"line":20,"items":items})
        })
        .collect();
    sections.push(json!({"name":section,"line":19,"prose":[{"text":"Introduction","line":19}],"labels":labels}));
    let mut bound = bind_file(&value);
    assert!(bound.diagnostics.is_empty(), "{:?}", bound.diagnostics);
    bound.requirements.remove(0)
}

#[test]
fn text_list_preserves_items_and_empty_optional_labels() {
    let row = bind_labels(
        "Success Criteria",
        &[("Test Evidence", &["unit", "integration"])],
    );
    assert_eq!(row.success_criteria.text, "Introduction");
    assert_eq!(row.success_criteria.test_evidence, ["unit", "integration"]);
    assert!(row.success_criteria.acceptance_criteria.is_empty());
    assert_eq!(row.dependencies, Dependencies::default());
}

#[test]
fn statement_list_collects_all_modals() {
    let row = bind_labels(
        "Requirement Statement",
        &[
            ("MUST Statements", &["persist"]),
            ("SHOULD Statements", &["report"]),
            ("MUST NOT Statements", &["lose"]),
        ],
    );
    let statements = serde_json::to_value(row.requirement_statement.statements).unwrap();
    assert_eq!(
        statements,
        json!([
            {"modal":"Must","text":"persist"},
            {"modal":"Should","text":"report"},
            {"modal":"MustNot","text":"lose"}
        ])
    );
}

#[test]
fn checklist_distinguishes_checked_unchecked_and_no_box() {
    let row = bind_labels(
        "Success Criteria",
        &[(
            "Acceptance Criteria",
            &["[x] stored", "[ ] retrieved", "reviewed"],
        )],
    );
    let items = serde_json::to_value(row.success_criteria.acceptance_criteria).unwrap();
    assert_eq!(
        items,
        json!([
            {"text":"stored","checked":true},
            {"text":"retrieved","checked":false},
            {"text":"reviewed","checked":null}
        ])
    );
}

#[test]
fn id_list_discards_link_path_and_preserves_note() {
    let row = bind_labels(
        "Dependencies",
        &[(
            "Requires",
            &["NFR-FIX-0001", "[ADR-FIX-0001](decision.md) — rationale"],
        )],
    );
    assert_eq!(
        serde_json::to_value(row.dependencies.requires).unwrap(),
        json!([
            {"id":"NFR-FIX-0001","note":null},
            {"id":"ADR-FIX-0001","note":"rationale"}
        ])
    );
}

#[test]
fn link_list_preserves_text_href_and_note() {
    let row = bind_labels(
        "Related Documents",
        &[(
            "Design Documents",
            &["[guide](guide.md)", "[design](design.md) — detail"],
        )],
    );
    assert_eq!(
        serde_json::to_value(row.related_documents.design_documents).unwrap(),
        json!([
            {"text":"guide","href":"guide.md","note":null},
            {"text":"design","href":"design.md","note":"detail"}
        ])
    );
}

#[test]
fn inventory_reports_dangling_reference_with_label_and_remedy() {
    let row = bind_labels(
        "Dependencies",
        &[("Requires", &["REQ-FIX-0001", "NFR-FIX-9999"])],
    );
    let diagnostics = check_inventory(&[row], &[]);
    assert_eq!(diagnostics.len(), 1);
    assert_eq!(diagnostics[0].rule, Rule::DanglingReference);
    assert_eq!(diagnostics[0].label.as_deref(), Some("Requires"));
    assert_eq!(diagnostics[0].id.as_ref().unwrap().0, "REQ-FIX-0001");
    assert_eq!(
        summarize(&diagnostics)["groups"][0]["remedy"],
        "Declare the referenced identifier or remove the reference."
    );
}

#[test]
fn edges_view_returns_fixture_edges() {
    let fixture: Value =
        serde_json::from_str(include_str!("../../../tests/fixtures/records.json")).unwrap();
    let connection = Connection::open_in_memory().unwrap();
    connection.execute_batch(&sql_ddl()).unwrap();
    connection.execute_batch("BEGIN DEFERRED").unwrap();
    for table in ["requirements", "decisions"] {
        for record in fixture[table].as_array().unwrap() {
            let fields = record.as_object().unwrap();
            let columns = fields.keys().cloned().collect::<Vec<_>>().join(", ");
            let marks = vec!["?"; fields.len()].join(", ");
            let values = fields.values().map(|v| {
                (!v.is_null()).then(|| {
                    v.as_str()
                        .map(str::to_owned)
                        .unwrap_or_else(|| v.to_string())
                })
            });
            connection
                .execute(
                    &format!("INSERT INTO {table} ({columns}) VALUES ({marks})"),
                    rusqlite::params_from_iter(values),
                )
                .unwrap();
        }
    }
    connection.execute_batch("COMMIT").unwrap();
    let mut query = connection
        .prepare("SELECT source, path, target, position FROM edges ORDER BY source, path")
        .unwrap();
    let edges: Vec<(String, String, String, i64)> = query
        .query_map([], |row| {
            Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?))
        })
        .unwrap()
        .map(Result::unwrap)
        .collect();
    assert_eq!(
        serde_json::to_value(edges).unwrap(),
        json!([
            [
                "ADR-FIX-0001",
                "related_documents.requirements",
                "REQ-FIX-0001",
                0
            ],
            ["REQ-FIX-0001", "dependencies.related", "ADR-FIX-0001", 0],
            ["REQ-FIX-0001", "dependencies.requires", "NFR-FIX-0001", 0]
        ])
    );
}
