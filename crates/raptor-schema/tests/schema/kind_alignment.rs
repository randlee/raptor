use super::common::fixture;
use raptor_schema::{ErrorCategory, RecordKind, TableId, accept, json_schema, sql_ddl};
use rusqlite::{Connection, params_from_iter};
use serde_json::{Value, json};

#[test]
fn root_id_kinds_match_the_sql_table_constraints() {
    for table_id in TableId::ALL {
        let table = table_id.name();
        for kind in RecordKind::ALL {
            let allowed = match kind {
                RecordKind::Req | RecordKind::Nfr => table_id == TableId::Req,
                RecordKind::Adr => table_id == TableId::Dec,
            };
            let id = format!("{}FIX-9999", kind.prefix());
            let mut row = fixture()[table][0].clone();
            row["id"] = json!(id);
            row["supersedes"] = Value::Null;
            row["superseded_by"] = Value::Null;
            let input = if table_id == TableId::Req {
                json!({"requirements": [row], "decisions": []})
            } else {
                json!({"requirements": [], "decisions": [row]})
            };
            let result = accept(&input.to_string());
            let admitted = match table_id {
                TableId::Req => result.batch.requirements().count() == 1,
                TableId::Dec => result.batch.decisions().count() == 1,
            };
            assert_eq!(admitted, allowed, "{table}: {id}");
            let root_errors: Vec<_> = result
                .errors
                .iter()
                .filter(|error| {
                    error.category == ErrorCategory::InvalidId && error.field_path.as_ref() == "/id"
                })
                .collect();
            if allowed {
                assert!(root_errors.is_empty());
            } else {
                assert_eq!(root_errors.len(), 1);
                assert_eq!(result.errors.len(), 1);
                assert!(root_errors[0].cause.contains(table));
                let schema = serde_json::to_value(&json_schema()[table]).unwrap();
                for prefix in schema["x-raptor-tables"][table]["id_prefixes"]
                    .as_array()
                    .unwrap()
                {
                    assert!(root_errors[0].cause.contains(prefix.as_str().unwrap()));
                }
                let wire = serde_json::to_value(root_errors[0]).unwrap();
                let keys: std::collections::BTreeSet<_> = wire
                    .as_object()
                    .unwrap()
                    .keys()
                    .map(String::as_str)
                    .collect();
                assert_eq!(
                    keys,
                    [
                        "category",
                        "table",
                        "record_position",
                        "field_path",
                        "item_index",
                        "offending_value",
                        "cause",
                        "message",
                        "recovery",
                        "allowed_values",
                        "first_occurrence_record_position"
                    ]
                    .into_iter()
                    .collect()
                );
                assert_eq!(
                    serde_json::to_value(&result).unwrap()["summary"]["counts"],
                    json!({"BAD_VALUE": 1})
                );
                assert_eq!(root_errors[0].table, Some(table_id));
                assert_eq!(
                    root_errors[0].record_position.map(|position| position.0),
                    Some(0)
                );
                assert_eq!(root_errors[0].offending_value.as_ref(), &json!(id));
            }
            let db = Connection::open_in_memory().unwrap();
            db.execute_batch(&sql_ddl()).unwrap();
            let object = input[table][0].as_object().unwrap();
            let names = object.keys().cloned().collect::<Vec<_>>().join(", ");
            let placeholders = vec!["?"; object.len()].join(", ");
            let values = object.values().map(|value| match value {
                Value::Null => None,
                Value::String(text) => Some(text.clone()),
                other => Some(other.to_string()),
            });
            let inserted = db
                .execute(
                    &format!("INSERT INTO {table} ({names}) VALUES ({placeholders})"),
                    params_from_iter(values),
                )
                .is_ok();
            assert_eq!(inserted, admitted, "SQL/ingress mismatch: {table} {id}");
        }
    }
}

#[test]
fn wrong_table_kind_is_reported_alongside_independent_errors() {
    let mut input = fixture();
    input["requirements"][0]["id"] = json!("ADR-FIX-9999");
    input["requirements"][0]["title"] = Value::Null;
    input["requirements"][0]["supersedes"] = json!("REQ-FIX-0001");
    let result = accept(&input.to_string());
    let errors: Vec<_> = result
        .errors
        .iter()
        .filter(|error| error.table == Some(TableId::Req))
        .collect();
    assert_eq!(
        errors
            .iter()
            .map(|error| error.category)
            .collect::<Vec<_>>(),
        [ErrorCategory::NullNotAllowed, ErrorCategory::InvalidId]
    );
    assert_eq!(
        errors[1].record_position.map(|position| position.0),
        Some(0)
    );
    assert_eq!(errors[1].offending_value.as_ref(), &json!("ADR-FIX-9999"));
}

#[test]
fn wrong_table_id_preserves_position_and_malformed_id_is_not_double_reported() {
    let mut input = fixture();
    let second = input["requirements"][0].clone();
    input["requirements"].as_array_mut().unwrap().push(second);
    input["requirements"][1]["id"] = json!("ADR-FIX-9999");
    let result = accept(&input.to_string());
    assert_eq!(result.batch.requirements().count(), 1);
    assert_eq!(result.batch.decisions().count(), 1);
    let error = result
        .errors
        .iter()
        .find(|error| {
            error.category == ErrorCategory::InvalidId
                && error.table == Some(TableId::Req)
                && error.record_position.map(|p| p.0) == Some(1)
        })
        .unwrap();
    assert_eq!(error.field_path.as_ref(), "/id");
    assert_eq!(error.offending_value.as_ref(), &json!("ADR-FIX-9999"));
    input["requirements"][1]["id"] = json!("ADR-X-1");
    let result = accept(&input.to_string());
    assert_eq!(
        result
            .errors
            .iter()
            .filter(|error| error.category == ErrorCategory::InvalidId
                && error.table == Some(TableId::Req)
                && error.record_position.map(|p| p.0) == Some(1)
                && error.field_path.as_ref() == "/id")
            .count(),
        1
    );
}

#[test]
fn wrong_table_duplicate_rejects_all_occurrences_and_leaves_reference_dangling() {
    let mut input = fixture();
    let mut unique = input["requirements"][0].clone();
    unique["id"] = json!("REQ-FIX-0002");
    unique["dependencies"]["related"] = json!([{"id": "REQ-FIX-0001", "note": null}]);
    input["requirements"].as_array_mut().unwrap().push(unique);
    input["decisions"][0]["id"] = json!("REQ-FIX-0001");
    let result = accept(&input.to_string());
    assert_eq!(result.batch.requirements().count(), 1);
    assert_eq!(result.batch.decisions().count(), 0);
    let categories = result
        .errors
        .iter()
        .map(|error| error.category)
        .collect::<Vec<_>>();
    assert_eq!(
        categories,
        [
            ErrorCategory::DuplicateId,
            ErrorCategory::InvalidId,
            ErrorCategory::DuplicateId,
            ErrorCategory::DanglingReference
        ]
    );
    assert_eq!(
        result.errors[3].offending_value.as_ref(),
        &json!("REQ-FIX-0001")
    );
}
