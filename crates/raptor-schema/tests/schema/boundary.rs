use raptor_schema::{MetaLevel, MetaShape, TableId, field_table, json_schema};
use serde_json::{Value, json};

#[test]
fn exported_roles_resolve_to_declared_properties() {
    let schemas = json_schema();
    for schema in schemas.values() {
        let json = serde_json::to_value(schema).unwrap();
        assert!(json["x-raptor-rules"]["BAD_VALUE"]["categories"].is_array());
        assert!(json["x-raptor-tables"]["requirements"].is_object());
        for definition in json["definitions"].as_object().unwrap().values() {
            if let Some(roles) = definition.get("x-raptor-roles").and_then(Value::as_object) {
                let properties = definition["properties"].as_object().unwrap();
                for property in roles.values() {
                    assert!(properties.contains_key(property.as_str().unwrap()));
                }
            }
        }
    }
    for field in field_table(TableId::Req)
        .into_iter()
        .filter(|field| field.modal.is_some())
    {
        assert!(field.modal_label_suffix.is_some());
    }
}

#[test]
fn root_properties_match_declared_stored_fields() {
    use std::collections::BTreeSet;
    let schemas = json_schema();
    for (name, table) in [("requirements", TableId::Req), ("decisions", TableId::Dec)] {
        let schema = serde_json::to_value(&schemas[name]).unwrap();
        let properties: BTreeSet<_> = schema["properties"]
            .as_object()
            .unwrap()
            .keys()
            .cloned()
            .collect();
        let fields: BTreeSet<_> = field_table(table)
            .into_iter()
            .filter(|field| field.level != MetaLevel::Label && field.shape != MetaShape::Derived)
            .map(|field| field.name.to_owned())
            .collect();
        assert_eq!(properties, fields);
    }
}

#[test]
fn each_nested_field_has_a_schema_property_in_its_section() {
    let schemas = json_schema();
    for (name, table) in [("requirements", TableId::Req), ("decisions", TableId::Dec)] {
        let schema = serde_json::to_value(&schemas[name]).unwrap();
        let fields = field_table(table);
        for label in fields
            .iter()
            .filter(|field| field.level == MetaLevel::Label)
        {
            let parent = fields
                .iter()
                .find(|field| {
                    field.level == MetaLevel::Section && Some(field.label) == label.section
                })
                .unwrap();
            let pointer = schema["properties"][parent.name]["$ref"].as_str().unwrap();
            let definition = &schema["definitions"][pointer.rsplit('/').next().unwrap()];
            let properties = &definition["properties"];
            let direct = properties.get(label.name).is_some();
            let grouped = properties
                .get("groups")
                .and_then(|group| group["items"]["$ref"].as_str())
                .and_then(|reference| {
                    schema["definitions"].get(reference.rsplit('/').next().unwrap())
                })
                .is_some_and(|group| group["properties"].get(label.name).is_some());
            assert!(
                direct || grouped,
                "{name}: {} / {}",
                parent.name,
                label.name
            );
        }
    }
}

#[test]
fn source_optional_fields_still_require_explicit_canonical_keys() {
    use super::common::fixture;
    use raptor_schema::{ErrorCategory, accept};
    let schema = serde_json::to_value(&json_schema()["requirements"]).unwrap();
    let fields = field_table(TableId::Req);
    let dependencies = fields
        .iter()
        .find(|field| field.name == "dependencies")
        .unwrap();
    assert!(!dependencies.required);
    assert!(
        schema["required"]
            .as_array()
            .unwrap()
            .contains(&"dependencies".into())
    );
    let supersedes = fields
        .iter()
        .find(|field| field.name == "supersedes")
        .unwrap();
    assert!(supersedes.nullable);
    assert!(
        !schema["required"]
            .as_array()
            .unwrap()
            .contains(&"supersedes".into())
    );
    for name in ["dependencies", "supersedes"] {
        let mut input = fixture();
        input["requirements"][0]
            .as_object_mut()
            .unwrap()
            .remove(name);
        let result = accept(&input.to_string());
        assert!(
            result
                .errors
                .iter()
                .any(|error| error.category == ErrorCategory::MissingKey
                    && error.field_path.as_ref() == format!("/{name}"))
        );
    }
}

#[test]
fn top_level_storage_nullability_matches_field_metadata() {
    for (name, table) in [("requirements", TableId::Req), ("decisions", TableId::Dec)] {
        let schema = serde_json::to_value(&json_schema()[name]).unwrap();
        for field in field_table(table)
            .iter()
            .filter(|field| field.level != MetaLevel::Label && field.shape != MetaShape::Derived)
        {
            let property = &schema["properties"][field.name];
            let nullable = property["anyOf"]
                .as_array()
                .is_some_and(|choices| choices.iter().any(|choice| choice["type"] == "null"));
            assert_eq!(nullable, field.nullable, "{name}: {}", field.name);
            let required = schema["required"]
                .as_array()
                .unwrap()
                .contains(&field.name.into());
            assert_eq!(required, !field.nullable, "{name}: {}", field.name);
        }
    }
}

#[test]
fn every_error_category_has_exactly_one_source_rule() {
    use raptor_schema::ErrorCategory;
    use std::collections::BTreeSet;
    let schema = serde_json::to_value(&json_schema()["requirements"]).unwrap();
    let categories: Vec<_> = schema["x-raptor-rules"]
        .as_object()
        .unwrap()
        .values()
        .flat_map(|rule| rule["categories"].as_array().unwrap().iter().cloned())
        .collect();
    let expected: BTreeSet<_> = ErrorCategory::ALL
        .into_iter()
        .map(|category| serde_json::to_string(&category).unwrap())
        .collect();
    let actual: BTreeSet<_> = categories
        .iter()
        .map(|category| serde_json::to_string(category).unwrap())
        .collect();
    assert_eq!(categories.len(), actual.len());
    assert_eq!(actual, expected);
}

#[test]
fn nested_section_properties_are_exposed_by_metadata() {
    use std::collections::BTreeSet;
    for (name, table) in [("requirements", TableId::Req), ("decisions", TableId::Dec)] {
        let schema = serde_json::to_value(&json_schema()[name]).unwrap();
        let fields = field_table(table);
        for section in fields
            .iter()
            .filter(|field| field.level == MetaLevel::Section)
        {
            let Some(reference) = schema["properties"][section.name]["$ref"].as_str() else {
                continue;
            };
            let definition = &schema["definitions"][reference.rsplit('/').next().unwrap()];
            let properties = definition["properties"].as_object().unwrap();
            let mut names: BTreeSet<_> = properties
                .keys()
                .filter(|key| *key != "text" && *key != "groups")
                .cloned()
                .collect();
            if let Some(reference) = properties
                .get("groups")
                .and_then(|group| group["items"]["$ref"].as_str())
            {
                let group =
                    &schema["definitions"][reference.rsplit('/').next().unwrap()]["properties"];
                names.extend(
                    group
                        .as_object()
                        .unwrap()
                        .keys()
                        .filter(|key| *key != "name")
                        .cloned(),
                );
            }
            let labels: BTreeSet<_> = fields
                .iter()
                .filter(|field| {
                    field.level == MetaLevel::Label && field.section == Some(section.label)
                })
                .map(|field| field.name.to_owned())
                .collect();
            assert_eq!(names, labels, "{name}: {}", section.name);
        }
    }
}

#[test]
fn heading_prefixes_match_table_kinds_and_scalar_validation() {
    use raptor_schema::{RecordKind, validate_scalar};
    let schemas = json_schema();
    for (table, expected) in [
        ("requirements", vec![RecordKind::Req, RecordKind::Nfr]),
        ("decisions", vec![RecordKind::Adr]),
    ] {
        let schema = serde_json::to_value(&schemas[table]).unwrap();
        let prefixes = schema["x-raptor-tables"][table]["id_prefixes"]
            .as_array()
            .unwrap();
        assert_eq!(prefixes.len(), expected.len());
        for (prefix, kind) in prefixes.iter().zip(expected) {
            assert_eq!(prefix.as_str(), Some(kind.prefix()));
            let id = format!("{}FIX-0001", kind.prefix());
            assert!(validate_scalar("Id", &id).is_ok());
            assert_eq!(RecordKind::from_id(&id), Some(kind));
        }
    }
}

#[test]
fn source_only_rules_are_exported_without_rust_error_categories() {
    use std::collections::BTreeSet;
    let schemas = json_schema();
    for schema in schemas.values() {
        let schema = serde_json::to_value(schema).unwrap();
        let rules = schema["x-raptor-rules"].as_object().unwrap();
        let source = [
            "MISSING_ID",
            "MISSING_FIELD",
            "UNKNOWN_SECTION",
            "UNKNOWN_LABEL",
        ];
        let rust = ["BAD_VALUE", "DUPLICATE_ID", "DANGLING_REFERENCE"];
        let expected: BTreeSet<_> = source.into_iter().chain(rust).collect();
        let actual: BTreeSet<_> = rules.keys().map(String::as_str).collect();
        assert_eq!(actual, expected);
        for rule in source {
            assert!(rules[rule]["categories"].as_array().unwrap().is_empty());
        }
        for rule in rust {
            assert!(!rules[rule]["categories"].as_array().unwrap().is_empty());
        }
    }
}

#[test]
fn protocol_vocabulary_and_heading_partition_are_pinned() {
    use std::collections::BTreeSet;
    let schemas = json_schema();
    let mut seen_semantic = BTreeSet::new();
    for (table, kind) in [("requirements", TableId::Req), ("decisions", TableId::Dec)] {
        let schema = serde_json::to_value(&schemas[table]).unwrap();
        let protocol = &schema["x-raptor-protocol"];
        assert_eq!(
            protocol["levels"],
            json!(["Header", "Item", "Section", "Label"])
        );
        assert_eq!(
            protocol["shapes"],
            json!([
                "Text",
                "Date",
                "Version",
                "Status",
                "Id",
                "IdList",
                "TextList",
                "StatementList",
                "Checklist",
                "LinkList",
                "Group",
                "Derived"
            ])
        );
        assert_eq!(
            protocol["roles"],
            json!([
                "heading_id",
                "heading_title",
                "item_label",
                "header_label",
                "section_label",
                "group",
                "section_prose"
            ])
        );
        assert_eq!(
            protocol["heading_roles"],
            json!({
                "identifier": "heading_id", "caption": "heading_title"
            })
        );
        assert_eq!(
            protocol["semantic_roles"],
            json!([
                "content",
                "selection",
                "identifier",
                "destination",
                "annotation",
                "modality",
                "caption",
                "collection"
            ])
        );
        let all_roles: BTreeSet<_> = protocol["roles"]
            .as_array()
            .unwrap()
            .iter()
            .map(|value| value.as_str().unwrap())
            .collect();
        let headings: BTreeSet<_> = protocol["heading_roles"]
            .as_object()
            .unwrap()
            .values()
            .map(|value| value.as_str().unwrap())
            .collect();
        assert_eq!(headings.len(), 2);
        assert!(headings.is_subset(&all_roles));
        for field in field_table(kind) {
            let field = serde_json::to_value(field).unwrap();
            assert!(all_roles.contains(field["role"].as_str().unwrap()));
            if headings.contains(field["role"].as_str().unwrap()) {
                assert_eq!(field["level"], "Item");
            }
        }
        for definition in schema["definitions"].as_object().unwrap().values() {
            if let Some(roles) = definition.get("x-raptor-roles").and_then(Value::as_object) {
                seen_semantic.extend(roles.keys().cloned());
            }
        }
    }
    let schema = serde_json::to_value(&schemas["requirements"]).unwrap();
    let declared: BTreeSet<_> = schema["x-raptor-protocol"]["semantic_roles"]
        .as_array()
        .unwrap()
        .iter()
        .map(|value| value.as_str().unwrap().to_owned())
        .collect();
    assert_eq!(seen_semantic, declared);
}
