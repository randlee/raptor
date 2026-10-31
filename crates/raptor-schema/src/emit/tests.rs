use super::*;
use std::collections::BTreeSet;
#[test]
fn reference_shapes_have_typed_accessors() {
    for field in FIELDS {
        let valid = match (field.shape, field.reference) {
            (Shape::IdList, Some(ReferenceAccess::List { decision, .. }))
                if matches!(field.level, Level::Label(_)) =>
            {
                field.table != FieldScope::All || decision.is_some()
            }
            (Shape::Supersession, Some(ReferenceAccess::Scalar { .. })) => true,
            (Shape::IdList, None) if matches!(field.level, Level::Section) => true,
            (Shape::IdList | Shape::Supersession, _) | (_, Some(_)) => false,
            _ => true,
        };
        assert!(valid, "invalid reference accessor for {}", field.name);
    }
}

#[test]
fn field_exports_cover_all_63_entries_with_derived_attributes() -> Result<(), serde_json::Error> {
    let mut exported = BTreeSet::new();
    for table in [TableId::Req, TableId::Dec] {
        let fields = field_table(table);
        let stored: Vec<_> = FIELDS
            .iter()
            .filter(|entry| {
                entry.table == FieldScope::Only(table) || entry.table == FieldScope::All
            })
            .collect();
        assert_eq!(fields.len(), stored.len());
        for (field, stored) in fields.iter().zip(stored) {
            assert_eq!((field.name, field.label), (stored.name, stored.label));
            assert_eq!(field.required, stored.presence == Presence::Required);
            assert_eq!(
                field.nullable,
                matches!(field.name, "supersedes" | "superseded_by")
            );
            assert_eq!(field.sql_type, "TEXT");
            let scope = match stored.table {
                FieldScope::Only(TableId::Req) => "Req",
                FieldScope::Only(TableId::Dec) => "Dec",
                FieldScope::All => "Both",
            };
            assert_eq!(serde_json::to_value(field.table)?, scope);
            assert_eq!(field.section.is_some(), field.level == MetaLevel::Label);
            exported.insert(serde_json::to_string(field)?);
        }
    }
    assert_eq!(exported.len(), 63);
    let modals: BTreeSet<_> = field_table(TableId::Req)
        .iter()
        .filter_map(|field| field.modal)
        .map(|modal| format!("{modal:?}"))
        .collect();
    let expected = ["Must", "Should", "MustNot"].map(String::from).into();
    assert_eq!(modals, expected);
    Ok(())
}

#[test]
fn id_prefix_checks_support_mixed_widths() -> Result<(), Box<dyn std::error::Error>> {
    let db = rusqlite::Connection::open_in_memory()?;
    let prefixes = ["R-".to_owned(), "LONG-".to_owned()];
    db.execute_batch(&format!(
        "CREATE TABLE ids (id TEXT{});",
        id_prefix_check("id", &prefixes)
    ))?;
    assert!(
        db.execute("INSERT INTO ids VALUES ('R-EXAMPLE')", [])
            .is_ok()
    );
    assert!(
        db.execute("INSERT INTO ids VALUES ('LONG-EXAMPLE')", [])
            .is_ok()
    );
    assert!(
        db.execute("INSERT INTO ids VALUES ('OTHER-EXAMPLE')", [])
            .is_err()
    );
    Ok(())
}
