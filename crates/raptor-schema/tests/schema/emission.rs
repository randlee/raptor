use super::common::fixture;
use raptor_schema::*;
use rusqlite::{Connection, params_from_iter};
use serde_json::{Value, json};
use std::collections::BTreeSet;

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
