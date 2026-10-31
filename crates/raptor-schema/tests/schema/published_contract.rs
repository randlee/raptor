use super::common::fixture;
use raptor_schema::{MetaLevel, MetaShape, TableId, field_table, json_schema};
use serde_json::{Value, json};
use std::collections::BTreeSet;

fn check_objects(node: &Value) {
    match node {
        Value::Object(object) => {
            if let Some(properties) = object.get("properties").and_then(Value::as_object) {
                let names: BTreeSet<_> = properties.keys().map(String::as_str).collect();
                let required: BTreeSet<_> = object
                    .get("required")
                    .and_then(Value::as_array)
                    .into_iter()
                    .flatten()
                    .map(|value| value.as_str().unwrap())
                    .collect();
                assert_eq!(names, required);
                assert_eq!(object.get("additionalProperties"), Some(&json!(false)));
            }
            for (name, value) in object {
                if !name.starts_with("x-raptor-") {
                    check_objects(value);
                }
            }
        }
        Value::Array(values) => values.iter().for_each(check_objects),
        _ => {}
    }
}

fn resolve<'a>(schema: &'a Value, node: &'a Value) -> &'a Value {
    if let Some(reference) = node.get("$ref").and_then(Value::as_str) {
        &schema["definitions"][reference.rsplit('/').next().unwrap()]
    } else if let Some(choices) = node.get("anyOf").and_then(Value::as_array) {
        resolve(
            schema,
            choices
                .iter()
                .find(|choice| choice["type"] != "null")
                .unwrap(),
        )
    } else {
        node
    }
}

#[test]
fn all_published_object_schemas_are_closed_and_require_every_property() {
    for schema in json_schema().values() {
        let schema = serde_json::to_value(schema).unwrap();
        check_objects(&schema);
        for definition in schema["definitions"].as_object().unwrap().values() {
            if let Some(roles) = definition.get("x-raptor-roles").and_then(Value::as_object) {
                for value in roles.values() {
                    assert!(
                        definition["properties"]
                            .get(value.as_str().unwrap())
                            .is_some()
                    );
                }
            }
        }
    }
}

#[test]
fn generic_validator_requires_nullable_keys_and_rejects_unknown_keys() {
    for table in ["requirements", "decisions"] {
        let schema = serde_json::to_value(&json_schema()[table]).unwrap();
        let validator = jsonschema::validator_for(&schema).unwrap();
        let row = fixture()[table][0].clone();
        assert!(validator.is_valid(&row));
        assert!(row["supersedes"].is_null());
        let mut missing = row.clone();
        missing.as_object_mut().unwrap().remove("supersedes");
        assert!(!validator.is_valid(&missing));
        let mut extra = row;
        extra["unexpected"] = json!(true);
        assert!(!validator.is_valid(&extra));
    }
}

#[test]
fn named_scalar_definitions_defer_semantics_to_rust() {
    for schema in json_schema().values() {
        let schema = serde_json::to_value(schema).unwrap();
        let serialized = schema.to_string();
        for name in ["Id", "Version", "Date"] {
            let definition = &schema["definitions"][name];
            assert_eq!(definition["type"], "string");
            assert!(definition.get("pattern").is_none());
            assert!(definition.get("format").is_none());
            assert!(
                definition["description"]
                    .as_str()
                    .unwrap()
                    .contains("validate_scalar")
            );
            assert!(serialized.contains(&format!("#/definitions/{name}")));
        }
    }
}

#[test]
fn source_shape_and_level_agree_with_stored_schema() {
    for (table, kind) in [("requirements", TableId::Req), ("decisions", TableId::Dec)] {
        let schema = serde_json::to_value(&json_schema()[table]).unwrap();
        let fields = field_table(kind);
        for field in &fields {
            if field.shape == MetaShape::Derived {
                continue;
            }
            let property = if field.level == MetaLevel::Label {
                let parent = fields
                    .iter()
                    .find(|candidate| {
                        candidate.level == MetaLevel::Section
                            && Some(candidate.label) == field.section
                    })
                    .unwrap();
                let section = resolve(&schema, &schema["properties"][parent.name]);
                if let Some(property) = section["properties"].get(field.name) {
                    property
                } else {
                    let group = resolve(&schema, &section["properties"]["groups"]["items"]);
                    group["properties"].get(field.name).unwrap()
                }
            } else {
                &schema["properties"][field.name]
            };
            let stored = resolve(&schema, property);
            if field.level == MetaLevel::Section {
                assert!(
                    stored["type"] == "string" || stored["type"] == "object",
                    "{table}: {}",
                    field.name
                );
                if stored["type"] == "object" {
                    assert!(stored["properties"].get("text").is_some());
                }
            } else if matches!(
                field.shape,
                MetaShape::IdList
                    | MetaShape::TextList
                    | MetaShape::StatementList
                    | MetaShape::Checklist
                    | MetaShape::LinkList
            ) {
                assert_eq!(stored["type"], "array", "{table}: {}", field.name);
            } else {
                assert_eq!(stored["type"], "string", "{table}: {}", field.name);
            }
        }
        let rationale = resolve(&schema, &schema["properties"]["rationale"]);
        assert_eq!(
            rationale["type"],
            if table == "requirements" {
                "string"
            } else {
                "object"
            }
        );
    }
}

#[test]
fn nullable_checkboxes_remain_three_state_but_the_key_is_required() {
    let schema = serde_json::to_value(&json_schema()["requirements"]).unwrap();
    let validator = jsonschema::validator_for(&schema).unwrap();
    for state in [Value::Null, json!(true), json!(false)] {
        let mut row = fixture()["requirements"][0].clone();
        row["success_criteria"]["acceptance_criteria"][0]["checked"] = state;
        assert!(validator.is_valid(&row));
    }
    let mut row = fixture()["requirements"][0].clone();
    row["success_criteria"]["acceptance_criteria"][0]
        .as_object_mut()
        .unwrap()
        .remove("checked");
    assert!(!validator.is_valid(&row));
}
