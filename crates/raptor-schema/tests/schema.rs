use raptor_schema::*;
use rusqlite::{Connection, params_from_iter};
use serde_json::{Value, json};
use std::collections::BTreeSet;

fn fixture() -> Value {
    let records = r#"{
      "requirements": [{
        "id": "REQ-FIX-0001", "title": "Persist records", "status": "Active",
        "version": "1.0.0", "created": "2000-02-29", "last_updated": "2026-01-01",
        "owner": "Example", "supersedes": null, "superseded_by": null,
        "requirement_statement": {"text": "Persist", "statements": [
          {"modal": "Must", "text": "Keep records"}]},
        "rationale": "Preserve information",
        "success_criteria": {"text": "Verified", "acceptance_criteria": [
          {"text": "Read back", "checked": null}], "test_evidence": []},
        "dependencies": {"text": "", "requires": [], "related": []},
        "product_applicability": {"text": "", "applies_to": [], "does_not_apply_to": []},
        "implementation_notes": {"text": "", "key_considerations": []},
        "test_strategy": {"text": "", "test_types": []},
        "related_documents": {"text": "", "requirements": [], "architecture_decisions": [],
          "design_documents": [], "work_items": [], "external_references": []}
      }],
      "decisions": [{
        "id": "ADR-FIX-0001", "title": "Storage", "status": "Approved",
        "version": "1.0.0", "created": "2000-02-29", "last_updated": "2026-01-01",
        "owner": "Example", "supersedes": null, "superseded_by": null,
        "decision_date": "2026-01-01",
        "context": {"text": "Need storage", "background": "", "problem_statement": ""},
        "decision": {"text": "Use a database", "chosen_approach": "", "key_principles": []},
        "rationale": {"text": "Durability", "benefits": [], "trade_offs": []},
        "consequences": {"text": "", "positive": [], "negative": [], "neutral": []},
        "alternatives": {"text": "", "groups": []},
        "implementation": {"text": "", "key_components": [], "integration_points": [],
          "code_examples": ""},
        "impact_analysis": {"text": "", "affected_components": "", "performance_impact": "",
          "security_impact": "", "maintainability_impact": ""},
        "related_documents": {"text": "", "requirements": [], "architecture_decisions": [],
          "design_documents": [], "work_items": [], "external_references": []}
      }]
    }"#;
    serde_json::from_str(records).unwrap()
}

fn check_error(
    error: &Error,
    category: &str,
    table: Option<&str>,
    position: Option<usize>,
    path: &str,
    item: Option<usize>,
    value: &Value,
) {
    assert_eq!(json!(error.category), category);
    assert_eq!(error.table.as_deref(), table);
    assert_eq!(error.record_position, position);
    assert_eq!(error.field_path.as_ref(), path);
    assert_eq!(error.item_index, item);
    assert_eq!(error.offending_value.as_ref(), value);
    assert!(!error.cause.is_empty());
    assert!(!error.message.is_empty());
}

fn reject(path: &str, value: Value, category: &str, item: Option<usize>) {
    let mut input = fixture();
    *input["requirements"][0].pointer_mut(path).unwrap() = value.clone();
    let result = accept(&input.to_string());
    assert_eq!(result.batch.requirements().count(), 0);
    assert_eq!(result.batch.decisions().count(), 1);
    assert_eq!(result.errors.len(), 1, "{:?}", result.errors);
    check_error(&result.errors[0], category, Some("requirements"), Some(0), path, item, &value);
    let output = serde_json::to_value(result).unwrap();
    assert_eq!(output["summary"]["counts"], json!({"BAD_VALUE": 1}));
}

#[test]
fn valid_batch_preserves_records_and_checkbox_states() {
    for checked in [Value::Null, json!(false), json!(true)] {
        let mut input = fixture();
        input["requirements"][0]["success_criteria"]["acceptance_criteria"][0]["checked"] = checked;
        let result = accept(&input.to_string());
        assert!(result.errors.is_empty(), "{:?}", result.errors);
        let output = serde_json::to_value(result).unwrap();
        assert_eq!(output["batch"], input);
        assert_eq!(output["summary"], json!({"records": 2, "counts": {}}));
    }
}

#[test]
fn strict_values_have_structured_errors() {
    for (path, value, category, item) in [
        ("/title", json!([]), "TypeMismatch", None),
        ("/title", Value::Null, "NullNotAllowed", None),
        ("/status", json!("active"), "UnknownVariant", None),
        ("/status", json!("Actve"), "UnknownVariant", None),
        ("/id", json!("REQ-X-1"), "InvalidId", None),
        ("/version", json!("1.10.0"), "InvalidVersion", None),
        ("/created", json!("2026-13-01"), "InvalidDate", None),
        ("/created", json!("2025-02-29"), "InvalidDate", None),
        ("/created", json!("1900-02-29"), "InvalidDate", None),
        ("/supersedes", json!("ADR-FIX-0001"), "CrossKindSupersession", None),
        ("/requirement_statement/statements/0/modal", json!("must"), "UnknownVariant", Some(0)),
    ] {
        reject(path, value, category, item);
    }
    for date in ["2000-02-29", "2024-02-29"] {
        let mut input = fixture();
        input["decisions"][0]["decision_date"] = json!(date);
        assert!(accept(&input.to_string()).errors.is_empty());
    }
}

#[test]
fn unknown_and_missing_keys_are_rejected_at_every_depth() {
    for (parent, key, item, missing) in [
        ("", "extra", None, false),
        ("/requirement_statement/statements/0", "extra", Some(0), false),
        ("", "owner", None, true),
        ("", "supersedes", None, true),
        ("", "superseded_by", None, true),
        ("/success_criteria/acceptance_criteria/0", "checked", Some(0), true),
    ] {
        let mut input = fixture();
        let object = input["requirements"][0]
            .pointer_mut(parent)
            .unwrap()
            .as_object_mut()
            .unwrap();
        let (category, value) = if missing {
            object.remove(key);
            ("MissingKey", Value::Null)
        } else {
            object.insert(key.into(), json!(42));
            ("UnknownKey", json!(42))
        };
        let result = accept(&input.to_string());
        assert_eq!(result.errors.len(), 1);
        assert_eq!(result.batch.requirements().count(), 0);
        let path = format!("{parent}/{key}");
        check_error(
            &result.errors[0],
            category,
            Some("requirements"),
            Some(0),
            &path,
            item,
            &value,
        );
        assert_eq!(
            serde_json::to_value(result).unwrap()["summary"]["counts"],
            json!({"BAD_VALUE": 1})
        );
    }
}

#[test]
fn malformed_batch_has_one_root_error() {
    for input in [
        json!(null),
        json!([]),
        json!({}),
        json!({"requirements": {}, "decisions": []}),
        json!({"requirements": [], "decisions": [], "extra": 1}),
    ] {
        let category = if input.get("extra").is_some() {
            "UnknownKey"
        } else {
            "TypeMismatch"
        };
        let result = accept(&input.to_string());
        assert_eq!(result.batch.requirements().count() + result.batch.decisions().count(), 0);
        assert_eq!(result.errors.len(), 1);
        check_error(&result.errors[0], category, None, None, "", None, &input);
    }
    let result = accept("{");
    assert_eq!(result.errors.len(), 1);
    check_error(&result.errors[0], "TypeMismatch", None, None, "", None, &json!("{"));
}

#[test]
fn mixed_batch_keeps_original_positions_and_collects_all_errors() {
    let mut input = fixture();
    let mut next = input["requirements"][0].clone();
    next["id"] = json!("REQ-FIX-0002");
    input["requirements"].as_array_mut().unwrap().push(next);
    input["requirements"][0]["title"] = Value::Null;
    let result = accept(&input.to_string());
    let positions = result.batch.requirements().map(|(position, _)| position);
    assert!(positions.eq([1]));
    assert_eq!(result.batch.decisions().count(), 1);
    assert_eq!(result.errors.len(), 1);
    check_error(
        &result.errors[0],
        "NullNotAllowed",
        Some("requirements"),
        Some(0),
        "/title",
        None,
        &Value::Null,
    );
    input["requirements"][0]["owner"] = json!(7);
    input["requirements"][0]["status"] = json!("active");
    let result = accept(&input.to_string());
    assert_eq!(result.errors.len(), 3);
    assert_eq!(serde_json::to_value(result).unwrap()["summary"]["counts"], json!({"BAD_VALUE": 3}));
}

#[test]
fn duplicates_report_every_occurrence_within_and_across_tables() {
    for (source, destination) in [
        ("requirements", "requirements"),
        ("decisions", "decisions"),
        ("requirements", "decisions"),
    ] {
        let mut input = fixture();
        let id = input[source][0]["id"].clone();
        if source == destination {
            let row = input[source][0].clone();
            input[destination].as_array_mut().unwrap().push(row);
        } else {
            input[destination][0]["id"] = id.clone();
        }
        let result = accept(&input.to_string());
        assert_eq!(result.errors.len(), 2);
        for (error, (table, position)) in result.errors.iter().zip([
            (source, 0),
            (destination, usize::from(source == destination)),
        ]) {
            check_error(error, "DuplicateId", Some(table), Some(position), "/id", None, &id);
        }
        assert_eq!(
            serde_json::to_value(result).unwrap()["summary"]["counts"],
            json!({"DUPLICATE_ID": 2})
        );
    }
}

#[test]
fn every_reference_group_and_supersession_reports_dangling_targets() {
    for table in ["requirements", "decisions"] {
        let mut paths = vec![
            "/related_documents/requirements",
            "/related_documents/architecture_decisions",
            "/supersedes",
            "/superseded_by",
        ];
        if table == "requirements" {
            paths.extend(["/dependencies/requires", "/dependencies/related"]);
        }
        for path in paths {
            let mut input = fixture();
            let target = if table == "requirements" {
                "REQ-FIX-9999"
            } else {
                "ADR-FIX-9999"
            };
            let slot = input[table][0].pointer_mut(path).unwrap();
            let item = slot.is_array().then_some(0);
            *slot = if item.is_some() {
                json!([{"id": target, "note": null}])
            } else {
                json!(target)
            };
            let result = accept(&input.to_string());
            assert_eq!(result.errors.len(), 1, "{table}{path}: {:?}", result.errors);
            check_error(
                &result.errors[0],
                "DanglingReference",
                Some(table),
                Some(0),
                path,
                item,
                &json!(target),
            );
            assert!(result.errors[0].message.contains(target));
            assert_eq!(
                serde_json::to_value(result).unwrap()["summary"]["counts"],
                json!({"DANGLING_REFERENCE": 1})
            );
        }
    }
}

#[test]
fn references_to_rejected_records_are_dangling() {
    let mut input = fixture();
    input["requirements"][0]["dependencies"]["related"] =
        json!([{"id": "ADR-FIX-0001", "note": null}]);
    input["decisions"][0]["title"] = Value::Null;
    let result = accept(&input.to_string());
    assert_eq!(result.batch.decisions().count(), 0);
    assert_eq!(result.errors.len(), 2);
    check_error(
        &result.errors[1],
        "DanglingReference",
        Some("requirements"),
        Some(0),
        "/dependencies/related",
        Some(0),
        &json!("ADR-FIX-0001"),
    );
    assert!(result.errors[1].message.contains("ADR-FIX-0001"));
    assert_eq!(
        serde_json::to_value(result).unwrap()["summary"]["counts"],
        json!({"BAD_VALUE": 1, "DANGLING_REFERENCE": 1})
    );
}

#[test]
fn field_exports_cover_all_63_entries_with_derived_attributes() {
    let mut exported = BTreeSet::new();
    for table in [Table::Req, Table::Dec] {
        let fields = field_table(table);
        let stored: Vec<_> = FIELDS
            .iter()
            .filter(|entry| entry.2 == table || entry.2 == Table::Both)
            .collect();
        assert_eq!(fields.len(), stored.len());
        for (field, stored) in fields.iter().zip(stored) {
            assert_eq!((field.name, field.label), (stored.0, stored.1));
            assert_eq!(field.required, stored.5 == Presence::Required);
            assert_eq!(field.nullable, matches!(field.name, "supersedes" | "superseded_by"));
            assert_eq!(field.sql_type, "TEXT");
            let scope = match stored.2 {
                Table::Req => "Req",
                Table::Dec => "Dec",
                Table::Both => "Both",
            };
            assert_eq!(field.table, scope);
            assert_eq!(field.section.is_some(), field.level == "Label");
            exported.insert(serde_json::to_string(field).unwrap());
        }
    }
    assert_eq!(exported.len(), 63);
    let modals: BTreeSet<_> = field_table(Table::Req)
        .iter()
        .filter_map(|field| field.modal)
        .map(|modal| format!("{modal:?}"))
        .collect();
    let expected = ["Must", "Should", "MustNot"].map(String::from).into();
    assert_eq!(modals, expected);
}

#[test]
fn emitted_json_schema_accepts_good_rows_and_rejects_wrong_types_and_enums() {
    let schemas = json_schema().unwrap();
    for (table, kind) in [("requirements", Table::Req), ("decisions", Table::Dec)] {
        let schema = serde_json::to_value(&schemas[table]).unwrap();
        assert_eq!(schema["x-raptor-fields"], serde_json::to_value(field_table(kind)).unwrap());
        let validator = jsonschema::validator_for(&schema).unwrap();
        let mut row = fixture()[table][0].clone();
        assert!(validator.is_valid(&row));
        row["status"] = json!("active");
        assert!(!validator.is_valid(&row));
        row = fixture()[table][0].clone();
        row["title"] = json!(123);
        assert!(!validator.is_valid(&row));
    }
}

#[test]
fn emitted_sql_loads_records_and_keeps_only_supersession_nullable() {
    let db = Connection::open_in_memory().unwrap();
    db.execute_batch(&sql_ddl()).unwrap();
    db.execute_batch("PRAGMA foreign_keys = ON; BEGIN DEFERRED")
        .unwrap();
    for table in ["requirements", "decisions"] {
        let row = fixture()[table][0].as_object().unwrap().clone();
        let mut info = db.prepare(&format!("PRAGMA table_info({table})")).unwrap();
        let columns: Vec<(String, String, bool)> = info
            .query_map([], |row| Ok((row.get(1)?, row.get(2)?, row.get(3)?)))
            .unwrap()
            .map(Result::unwrap)
            .collect();
        assert_eq!(columns.len(), row.len());
        for (name, kind, not_null) in columns {
            assert!(row.contains_key(&name));
            assert_eq!(kind, "TEXT");
            assert_eq!(not_null, !matches!(name.as_str(), "supersedes" | "superseded_by"));
        }
        let names = row.keys().cloned().collect::<Vec<_>>().join(", ");
        let marks = vec!["?"; row.len()].join(", ");
        let values = row.values().map(|value| match value {
            Value::Null => None,
            Value::String(text) => Some(text.clone()),
            other => Some(other.to_string()),
        });
        db.execute(
            &format!("INSERT INTO {table} ({names}) VALUES ({marks})"),
            params_from_iter(values),
        )
        .unwrap();
        let count: usize = db
            .query_row(&format!("SELECT COUNT(*) FROM {table}"), [], |row| row.get(0))
            .unwrap();
        assert_eq!(count, 1);
    }
    db.execute_batch("COMMIT").unwrap();
}
