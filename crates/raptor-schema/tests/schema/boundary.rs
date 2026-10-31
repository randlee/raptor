use raptor_schema::{MetaLevel, MetaShape, Table, field_table, json_schema};
use serde_json::Value;

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
    for field in field_table(Table::Req)
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
    for (name, table) in [("requirements", Table::Req), ("decisions", Table::Dec)] {
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
    for (name, table) in [("requirements", Table::Req), ("decisions", Table::Dec)] {
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
    let fields = field_table(Table::Req);
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
    for (name, table) in [("requirements", Table::Req), ("decisions", Table::Dec)] {
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
    for (name, table) in [("requirements", Table::Req), ("decisions", Table::Dec)] {
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
