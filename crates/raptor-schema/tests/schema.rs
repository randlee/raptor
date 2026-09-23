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
    Connection::open_in_memory()
        .unwrap()
        .execute_batch(&sql_ddl())
        .unwrap();
    assert!(field_table("requirements").len() > 9);
    assert_eq!(
        field_table("requirements")
            .into_iter()
            .filter(|field| field.name == "status")
            .map(|field| field.level)
            .collect::<Vec<_>>(),
        [Level::Header, Level::Item]
    );
    let fields = |table| {
        field_table(table)
            .into_iter()
            .filter(|field| field.name != "id_range" && field.level != Level::Label)
            .fold(Vec::new(), |mut names, field| {
                if !names.contains(&field.name) {
                    names.push(field.name)
                };
                names
            })
    };
    let names = |value: serde_json::Value| {
        value
            .as_object()
            .unwrap()
            .keys()
            .cloned()
            .collect::<std::collections::HashSet<_>>()
    };
    assert_eq!(
        fields("requirements")
            .into_iter()
            .map(String::from)
            .collect::<std::collections::HashSet<_>>(),
        names(serde_json::to_value(&requirements[0]).unwrap())
    );
    assert_eq!(
        fields("decisions")
            .into_iter()
            .map(String::from)
            .collect::<std::collections::HashSet<_>>(),
        names(serde_json::to_value(&decisions[0]).unwrap())
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
            requirement_statement: Default::default(),
            rationale: String::new(),
            success_criteria: Default::default(),
            dependencies: Default::default(),
            product_applicability: Default::default(),
            implementation_notes: Default::default(),
            test_strategy: Default::default(),
            related_documents: Default::default(),
        },
        Requirement {
            identity: Identity {
                id,
                title: "B".into(),
            },
            lifecycle,
            requirement_statement: Default::default(),
            rationale: String::new(),
            success_criteria: Default::default(),
            dependencies: Default::default(),
            product_applicability: Default::default(),
            implementation_notes: Default::default(),
            test_strategy: Default::default(),
            related_documents: Default::default(),
        },
    ];
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
