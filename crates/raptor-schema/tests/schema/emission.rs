use super::common::fixture;
use raptor_schema::*;
use rusqlite::{Connection, params_from_iter};
use serde_json::{Value, json};

fn insert_row(db: &Connection, table: &str, row: &Value) -> rusqlite::Result<()> {
    let object = row.as_object().expect("fixture rows are objects");
    let names = object.keys().cloned().collect::<Vec<_>>();
    let columns = names.join(", ");
    let marks = vec!["?"; names.len()].join(", ");
    let values = names.iter().map(|name| match &object[name] {
        Value::Null => None,
        Value::String(value) => Some(value.clone()),
        value => Some(value.to_string()),
    });
    db.execute(
        &format!("INSERT INTO {table} ({columns}) VALUES ({marks})"),
        params_from_iter(values),
    )?;
    Ok(())
}

fn foreign_key_violations(db: &Connection) -> Vec<String> {
    db.prepare("PRAGMA foreign_key_check")
        .unwrap()
        .query_map([], |row| row.get(0))
        .unwrap()
        .map(Result::unwrap)
        .collect()
}

#[test]
fn emitted_json_schema_accepts_good_rows_and_rejects_wrong_types_and_enums() {
    let schemas = json_schema();
    for (table, kind) in [("requirements", TableId::Req), ("decisions", TableId::Dec)] {
        let schema = serde_json::to_value(&schemas[table]).unwrap();
        assert_eq!(
            schema["x-raptor-fields"],
            serde_json::to_value(field_table(kind)).unwrap()
        );
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
            assert_eq!(
                not_null,
                !matches!(name.as_str(), "supersedes" | "superseded_by")
            );
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
            .query_row(&format!("SELECT COUNT(*) FROM {table}"), [], |row| {
                row.get(0)
            })
            .unwrap();
        assert_eq!(count, 1);
    }
    db.execute_batch("COMMIT").unwrap();
}

#[test]
fn emitted_sql_checks_schema_status_and_table_id_prefixes() {
    let data = fixture();
    let db = Connection::open_in_memory().unwrap();
    db.execute_batch(&sql_ddl()).unwrap();

    let mut invalid_status = data["requirements"][0].clone();
    invalid_status["status"] = json!("NotAStatus");
    assert!(insert_row(&db, "requirements", &invalid_status).is_err());

    let mut wrong_prefix = data["requirements"][0].clone();
    wrong_prefix["id"] = json!("ADR-FIX-0001");
    assert!(insert_row(&db, "requirements", &wrong_prefix).is_err());

    db.execute_batch("PRAGMA foreign_keys = ON; BEGIN DEFERRED")
        .unwrap();
    let req = data["requirements"][0].clone();
    let mut nfr = req.clone();
    nfr["id"] = json!("NFR-FIX-0001");
    insert_row(&db, "requirements", &req).unwrap();
    insert_row(&db, "requirements", &nfr).unwrap();

    let mut first_decision = data["decisions"][0].clone();
    first_decision["superseded_by"] = json!("ADR-FIX-0002");
    let mut second_decision = first_decision.clone();
    second_decision["id"] = json!("ADR-FIX-0002");
    second_decision["supersedes"] = json!("ADR-FIX-0001");
    second_decision["superseded_by"] = Value::Null;
    insert_row(&db, "decisions", &first_decision).unwrap();
    insert_row(&db, "decisions", &second_decision).unwrap();
    assert!(foreign_key_violations(&db).is_empty());
    db.execute_batch("COMMIT").unwrap();
}

#[test]
fn emitted_sql_reports_and_rejects_missing_supersession_targets() {
    let data = fixture();
    let db = Connection::open_in_memory().unwrap();
    db.execute_batch(&sql_ddl()).unwrap();
    db.execute_batch("PRAGMA foreign_keys = ON; BEGIN DEFERRED")
        .unwrap();
    let mut missing_target = data["decisions"][0].clone();
    missing_target["supersedes"] = json!("ADR-FIX-9999");
    missing_target["superseded_by"] = Value::Null;
    insert_row(&db, "decisions", &missing_target).unwrap();

    assert_eq!(foreign_key_violations(&db), ["decisions".to_owned()]);
    assert!(db.execute_batch("COMMIT").is_err());
    db.execute_batch("ROLLBACK").unwrap();
}

#[test]
fn edges_view_preserves_all_six_reference_paths_and_item_positions() {
    let mut records: Value =
        serde_json::from_str(include_str!("../../../../tests/fixtures/records.json")).unwrap();
    let requirement_targets = ["REQ-FIX-0001", "NFR-FIX-0001"];
    let decision_targets = ["ADR-FIX-0001", "ADR-FIX-0002"];
    let cases = [
        (
            "requirements",
            "dependencies",
            "requires",
            requirement_targets,
        ),
        ("requirements", "dependencies", "related", decision_targets),
        (
            "requirements",
            "related_documents",
            "requirements",
            requirement_targets,
        ),
        (
            "requirements",
            "related_documents",
            "architecture_decisions",
            decision_targets,
        ),
        (
            "decisions",
            "related_documents",
            "requirements",
            requirement_targets,
        ),
        (
            "decisions",
            "related_documents",
            "architecture_decisions",
            decision_targets,
        ),
    ];
    let mut expected = Vec::new();
    for (table, section, field, targets) in cases {
        records[table][0][section][field] =
            json!(targets.map(|target| json!({"id": target, "note": null})));
        let source = records[table][0]["id"].as_str().unwrap();
        for (position, target) in targets.into_iter().enumerate() {
            expected.push((
                source.to_owned(),
                format!("{section}.{field}"),
                target.to_owned(),
                position as i64,
            ));
        }
    }
    let accepted = accept(&records.to_string());
    assert!(accepted.errors.is_empty(), "{:?}", accepted.errors);
    let db = Connection::open_in_memory().unwrap();
    db.execute_batch(&sql_ddl()).unwrap();
    db.execute_batch("PRAGMA foreign_keys = ON; BEGIN DEFERRED")
        .unwrap();
    for table in ["requirements", "decisions"] {
        for row in records[table].as_array().unwrap() {
            insert_row(&db, table, row).unwrap();
        }
    }
    assert!(foreign_key_violations(&db).is_empty());
    db.execute_batch("COMMIT").unwrap();
    let actual: Vec<(String, String, String, i64)> = db
        .prepare("SELECT source, path, target, position FROM edges ORDER BY source, path, position")
        .unwrap()
        .query_map([], |row| {
            Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?))
        })
        .unwrap()
        .map(Result::unwrap)
        .collect();
    expected.sort_by(|left, right| (&left.0, &left.1, left.3).cmp(&(&right.0, &right.1, right.3)));
    assert_eq!(actual.len(), 12);
    assert_eq!(actual, expected);
}
