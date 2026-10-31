use super::common::{check_error, fixture};
use raptor_schema::*;
use serde_json::{Value, json};

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
            assert_eq!(
                error.cause.as_ref(),
                "a unique identifier; first occurrence is record position 0"
            );
            assert_eq!(error.first_occurrence_record_position.as_deref(), Some(&0));
            assert!(error.allowed_values.is_none());
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
            assert_eq!(output["summary"]["counts"], json!({"DANGLING_REFERENCE": 1}));
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
    assert_eq!(serde_json::to_vec(&result.errors[0]).unwrap(), expected.as_bytes());
}
