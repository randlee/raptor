use super::*;
use schemars::schema::SchemaObject;

#[test]
fn unresolvable_schema_reference_reports_type_mismatch() -> Result<(), Box<dyn std::error::Error>> {
    let schema = SchemaObject {
        reference: Some("#/definitions/Absent".to_owned()),
        ..SchemaObject::default()
    };
    let definitions = Default::default();
    let errors = Walker {
        definitions: &definitions,
        ids: BTreeMap::new(),
        typed: false,
    }
    .walk(&json!("value"), &schema, "/field", None);
    let error = errors.first().ok_or("missing error")?;
    assert_eq!(errors.len(), 1);
    assert_eq!(error.category, ErrorCategory::TypeMismatch);
    assert_eq!(error.field_path.as_ref(), "/field");
    assert_eq!(error.cause.as_ref(), "a resolvable schema reference");
    Ok(())
}

#[test]
fn decode_record_reports_serde_failure() -> Result<(), Box<dyn std::error::Error>> {
    let error = decode_record(TableId::Req, &json!({"id": 4}))
        .err()
        .ok_or("decode unexpectedly succeeded")?;
    assert!(!error.to_string().is_empty());
    Ok(())
}

#[test]
fn divergent_schema_returns_structured_decode_failure() -> Result<(), Box<dyn std::error::Error>> {
    // This local schema models future schema/serde drift, not a reachable
    // configuration of the generated production schema.
    let mut schema = emit::table_schema(TableId::Req);
    let Some(schemars::schema::Schema::Object(status)) = schema.definitions.get_mut("Status")
    else {
        return Err("missing Status definition".into());
    };
    status.enum_values = None;
    let fixture: Value =
        serde_json::from_str(include_str!("../../../../tests/fixtures/records.json"))?;
    let mut record = fixture
        .get("requirements")
        .and_then(Value::as_array)
        .and_then(|rows| rows.first())
        .cloned()
        .ok_or("missing requirement")?;
    *record.get_mut("status").ok_or("missing status")? = json!("invalid-status");
    let fields = emit::field_table(TableId::Req);
    assert!(check_record(&record, &schema, &fields, TableId::Req, None).is_empty());
    let mut accepted = Accepted {
        batch: Batch::new(),
        errors: Vec::new(),
    };
    process_records(
        &mut accepted,
        TableId::Req,
        std::iter::once((1, &record)),
        &schema,
        &fields,
        &crate::inventory::DuplicateIndex::default(),
    );
    assert_eq!(accepted.batch.requirements().count(), 0);
    assert_eq!(accepted.batch.decisions().count(), 0);
    assert_eq!(accepted.errors.len(), 1);
    let error = accepted.errors.first().ok_or("missing decode error")?;
    assert_eq!(error.category, ErrorCategory::TypeMismatch);
    assert_eq!(error.table, Some(TableId::Req));
    assert_eq!(error.record_position, Some(RecordPosition(1)));
    assert!(error.cause.starts_with("a valid requirements record ("));
    assert_eq!(error.offending_value.as_ref(), &record);
    assert!(crate::inventory::check_inventory(&accepted.batch).is_empty());
    Ok(())
}
