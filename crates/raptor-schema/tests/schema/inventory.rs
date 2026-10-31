use super::common::{check_error, fixture};
use raptor_schema::*;
use serde_json::{Value, json};

#[test]
fn duplicates_report_every_occurrence_within_each_table() {
    for (source, destination) in [("requirements", "requirements"), ("decisions", "decisions")] {
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
        assert_eq!(
            result.batch.requirements().count(),
            usize::from(source != "requirements")
        );
        assert_eq!(
            result.batch.decisions().count(),
            usize::from(source != "decisions")
        );
        for (error, (table, position)) in result.errors.iter().zip([
            (source, 0),
            (destination, usize::from(source == destination)),
        ]) {
            check_error(
                error,
                "DuplicateId",
                Some(table),
                Some(position),
                "/id",
                None,
                &id,
            );
            assert_eq!(
                error.cause.as_ref(),
                "a unique identifier; first occurrence is record position 0"
            );
            assert_eq!(
                error
                    .first_occurrence_record_position()
                    .map(|position| position.0),
                Some(0)
            );
            assert!(error.allowed_values().is_none());
            assert!(error.message.contains(error.cause.as_ref()));
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
            let output = serde_json::to_value(result).unwrap();
            assert_eq!(output["errors"][0]["table"], table);
            assert_eq!(
                output["summary"]["counts"],
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
fn dangling_reference_wire_matches_695781b() {
    let mut input = fixture();
    input["requirements"][0]["dependencies"]["requires"] =
        json!([{"id": "REQ-FIX-9999", "note": null}]);
    let result = accept(&input.to_string());
    assert_eq!(result.errors.len(), 1);
    let expected = concat!(
        r#"{"category":"DanglingReference","table":"requirements","record_position":0,"#,
        r#""field_path":"/dependencies/requires","item_index":0,"#,
        r#""offending_value":"REQ-FIX-9999","cause":"a referenced record in the batch","#,
        r#""message":"Found \"REQ-FIX-9999\"; expected a referenced record in the batch.","#,
        r#""recovery":"Create the referenced record or correct the reference.","#,
        r#""allowed_values":null,"first_occurrence_record_position":null}"#,
    );
    assert_eq!(
        serde_json::to_vec(&result.errors[0]).unwrap(),
        expected.as_bytes()
    );
}

#[test]
fn every_metadata_reference_is_checked() {
    for (table_name, table, target) in [
        ("requirements", TableId::Req, "REQ-FIX-9999"),
        ("decisions", TableId::Dec, "ADR-FIX-9999"),
    ] {
        let mut input = fixture();
        let fields = field_table(table);
        let mut paths = std::collections::BTreeSet::new();
        for field in &fields {
            if field.supersession {
                input[table_name][0][field.name] = json!(target);
                paths.insert(format!("/{}", field.name));
            } else if field.level == MetaLevel::Label && field.shape == MetaShape::IdList {
                let parent = fields
                    .iter()
                    .find(|parent| {
                        parent.level == MetaLevel::Section && Some(parent.label) == field.section
                    })
                    .unwrap();
                input[table_name][0][parent.name][field.name] =
                    json!([{"id": target, "note": null}]);
                paths.insert(format!("/{}/{}", parent.name, field.name));
            }
        }
        let result = accept(&input.to_string());
        let found = result
            .errors
            .iter()
            .filter(|error| {
                error.category == ErrorCategory::DanglingReference
                    && error.table
                        == Some(if table == TableId::Req {
                            TableId::Req
                        } else {
                            TableId::Dec
                        })
            })
            .map(|error| error.field_path.to_string())
            .collect();
        assert_eq!(paths, found);
    }
}

#[test]
fn inventory_diagnostic_order_preserves_related_dependencies_then_supersession() {
    let mut input = fixture();
    input["requirements"][0]["related_documents"]["requirements"] =
        json!([{"id": "REQ-FIX-9998", "note": null}]);
    input["requirements"][0]["dependencies"]["requires"] =
        json!([{"id": "REQ-FIX-9999", "note": null}]);
    input["requirements"][0]["supersedes"] = json!("REQ-FIX-9997");
    let result = accept(&input.to_string());
    let paths: Vec<_> = result
        .errors
        .iter()
        .map(|error| error.field_path.as_ref())
        .collect();
    assert_eq!(
        paths,
        [
            "/related_documents/requirements",
            "/dependencies/requires",
            "/supersedes"
        ]
    );
}

#[test]
fn cross_table_duplicate_rejects_both_and_preserves_wrong_kind_error() {
    let mut input = fixture();
    input["decisions"][0]["id"] = input["requirements"][0]["id"].clone();
    let result = accept(&input.to_string());
    assert_eq!(result.batch.decisions().count(), 0);
    assert!(
        result
            .errors
            .iter()
            .any(|error| error.category == ErrorCategory::InvalidId
                && error.table == Some(TableId::Dec)
                && error.field_path.as_ref() == "/id")
    );
    assert_eq!(result.batch.requirements().count(), 0);
    assert_eq!(
        result
            .errors
            .iter()
            .filter(|error| error.category == ErrorCategory::DuplicateId)
            .count(),
        2
    );
}

#[test]
fn duplicate_rows_never_win_even_if_conflicting_or_malformed() {
    for malformed in [false, true] {
        let mut input = fixture();
        let mut unique = input["requirements"][0].clone();
        unique["id"] = json!("REQ-FIX-0002");
        unique["dependencies"]["requires"] = json!([{"id": "REQ-FIX-0001", "note": null}]);
        let mut duplicate = input["requirements"][0].clone();
        duplicate["title"] = if malformed {
            Value::Null
        } else {
            json!("Conflicting")
        };
        let records = input["requirements"].as_array_mut().unwrap();
        records.insert(0, unique);
        records.push(duplicate);
        let result = accept(&input.to_string());
        let retained: Vec<_> = result
            .batch
            .requirements()
            .map(|row| row.position.0)
            .collect();
        assert_eq!(retained, [0]);
        let duplicates: Vec<_> = result
            .errors
            .iter()
            .filter(|e| e.category == ErrorCategory::DuplicateId)
            .collect();
        assert_eq!(duplicates.len(), 2);
        assert_eq!(
            duplicates
                .iter()
                .map(|e| e.record_position.unwrap().0)
                .collect::<Vec<_>>(),
            [1, 2]
        );
        assert!(
            duplicates
                .iter()
                .all(|e| e.first_occurrence_record_position().unwrap().0 == 1)
        );
        assert_eq!(
            result
                .errors
                .iter()
                .filter(|e| e.category == ErrorCategory::DanglingReference)
                .count(),
            1
        );
        assert_eq!(
            result
                .errors
                .iter()
                .filter(|e| e.category == ErrorCategory::NullNotAllowed)
                .count(),
            usize::from(malformed)
        );
    }
}

#[test]
fn duplicate_malformed_id_strings_keep_scalar_errors() {
    let mut input = fixture();
    input["requirements"][0]["id"] = json!("invalid");
    let row = input["requirements"][0].clone();
    input["requirements"].as_array_mut().unwrap().push(row);
    let result = accept(&input.to_string());
    assert_eq!(result.batch.requirements().count(), 0);
    assert_eq!(
        result
            .errors
            .iter()
            .filter(|e| e.category == ErrorCategory::DuplicateId)
            .count(),
        2
    );
    assert_eq!(
        result
            .errors
            .iter()
            .filter(|e| e.category == ErrorCategory::InvalidId)
            .count(),
        2
    );
}
