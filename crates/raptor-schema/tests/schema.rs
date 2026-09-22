use raptor_schema::*;
use rusqlite::Connection;
use serde_json::{Value, json};

fn tree() -> Value {
    json!({"path":"records.md","header":{"Status":{"value":"Draft","line":2},"Version":{"value":"1.0.0","line":3},"Created":{"value":"2026-01-01","line":4},"Last Updated":{"value":"2026-01-02","line":5},"Owner":{"value":"Example","line":6}},"records":[{"id":"REQ-FIX-0001","title":"Requirement","line":9,"fields":{"Status":{"value":"Active","line":10}}}]})
}
fn only(bound: &Bound, rule: Rule) -> &Diagnostic {
    assert_eq!(bound.diagnostics.len(), 1);
    let diagnostic = &bound.diagnostics[0];
    assert_eq!(diagnostic.rule, rule);
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
    Connection::open_in_memory()
        .unwrap()
        .execute_batch(&sql_ddl())
        .unwrap();
    assert_eq!(field_table("requirements").len(), 8);
    assert_eq!(
        field_table("decisions")
            .into_iter()
            .filter(|field| field.name != "id_range")
            .map(|field| field.name)
            .collect::<Vec<_>>(),
        [
            "id",
            "title",
            "status",
            "version",
            "created",
            "last_updated",
            "owner"
        ]
    );
    let validator = jsonschema::validator_for(&json_schema()).unwrap();
    assert!(validator.validate(&fixture).is_ok());
}

#[test]
fn inventory_reports_each_duplicate() {
    let id: Id = "REQ-FIX-0001".parse().unwrap();
    let lifecycle = Lifecycle {
        status: Status::Draft,
        version: "1.0.0".parse().unwrap(),
        created: "2026-01-01".parse().unwrap(),
        last_updated: "2026-01-01".parse().unwrap(),
        owner: "Example".into(),
    };
    let rows = vec![
        Requirement {
            identity: Identity {
                id: id.clone(),
                title: "A".into(),
            },
            lifecycle: lifecycle.clone(),
        },
        Requirement {
            identity: Identity {
                id,
                title: "B".into(),
            },
            lifecycle,
        },
    ];
    assert_eq!(check_inventory(&rows, &[]).len(), 2);
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
    assert_eq!(
        (
            diagnostic.file.as_str(),
            diagnostic.line,
            diagnostic.label.as_deref()
        ),
        ("records.md", 9, None)
    );
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
    value["records"][0]["sections"] = json!([{"name":"Extra","line":12,"labels":[]}]);
    let bound = bind_file(&value);
    let diagnostic = only(&bound, Rule::UnknownSection);
    assert_eq!(
        (
            diagnostic.line,
            diagnostic.label.as_deref(),
            diagnostic.allowed.as_ref().unwrap()
        ),
        (12, Some("Extra"), &vec![])
    );
    assert_eq!(bound.requirements.len(), 1);
}

#[test]
fn unknown_label_keeps_row() {
    let mut value = tree();
    value["records"][0]["fields"]["Priority"] = json!({"value":"high","line":11});
    let bound = bind_file(&value);
    let diagnostic = only(&bound, Rule::UnknownLabel);
    assert_eq!(
        (diagnostic.line, diagnostic.label.as_deref()),
        (11, Some("Priority"))
    );
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
