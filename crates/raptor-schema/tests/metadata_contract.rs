//! Both exported metadata paths must serialize the same consumed protocol.
use raptor_schema::{TableId, field_table, json_schema};

#[test]
fn serialized_field_table_matches_schema_extension_for_every_table() {
    let schemas = json_schema();
    for table in TableId::ALL {
        let fields = serde_json::to_value(field_table(table)).unwrap();
        assert_eq!(
            fields,
            schemas[table.name()].schema.extensions["x-raptor-fields"]
        );
    }
}
