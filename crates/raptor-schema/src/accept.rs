use crate::{
    batch::Batch,
    emit,
    error::{Error, ErrorCategory, ItemIndex, RecordPosition, TableId},
    schema::*,
};
use serde::{Deserialize, Serialize, Serializer};
use serde_json::{Value, json};
use std::sync::OnceLock;

#[derive(Debug)]
pub struct Accepted {
    pub batch: Batch,
    pub errors: Vec<Error>,
}

impl Serialize for Accepted {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        #[derive(Serialize)]
        struct Output<'a> {
            batch: &'a Batch,
            errors: &'a [Error],
            summary: crate::inventory::Summary,
        }
        Output {
            batch: &self.batch,
            errors: &self.errors,
            summary: crate::inventory::summarize(&self.batch, &self.errors),
        }
        .serialize(serializer)
    }
}

fn walk_target(
    value: &Value,
    schema: &schemars::schema::Schema,
    definitions: &schemars::Map<String, schemars::schema::Schema>,
    path: &str,
    item: Option<ItemIndex>,
) -> Vec<Error> {
    match schema {
        schemars::schema::Schema::Object(object) => walk(value, object, definitions, path, item),
        schemars::schema::Schema::Bool(_) => Vec::new(),
    }
}

fn walk_object(
    object: &serde_json::Map<String, Value>,
    properties: &schemars::Map<String, schemars::schema::Schema>,
    definitions: &schemars::Map<String, schemars::schema::Schema>,
    path: &str,
    item: Option<ItemIndex>,
) -> Vec<Error> {
    let mut errors = Vec::new();
    for (name, found) in object
        .iter()
        .filter(|(name, _)| !properties.contains_key(*name))
    {
        errors.push(
            Error::new(ErrorCategory::UnknownKey, found.clone(), "a declared key")
                .at(&format!("{path}/{name}"), item),
        );
    }
    for (name, specification) in properties {
        let field_path = format!("{path}/{name}");
        if let Some(found) = object.get(name) {
            errors.extend(walk_target(
                found,
                specification,
                definitions,
                &field_path,
                item,
            ));
        } else {
            errors.push(
                Error::new(ErrorCategory::MissingKey, Value::Null, "an explicit key")
                    .at(&field_path, item),
            );
        }
    }
    errors
}

fn walk_array(
    items: &[Value],
    specification: &schemars::schema::Schema,
    definitions: &schemars::Map<String, schemars::schema::Schema>,
    path: &str,
) -> Vec<Error> {
    items
        .iter()
        .enumerate()
        .flat_map(|(index, found)| {
            walk_target(
                found,
                specification,
                definitions,
                &format!("{path}/{index}"),
                Some(ItemIndex(index)),
            )
        })
        .collect()
}

// This ingress walker implements the emitted schema subset: references, nullable
// anyOf, instance types, enums, object properties, and array items. It requires
// every declared property explicitly, even when a nullable source field is absent.
fn walk(
    value: &Value,
    schema: &schemars::schema::SchemaObject,
    definitions: &schemars::Map<String, schemars::schema::Schema>,
    path: &str,
    item: Option<ItemIndex>,
) -> Vec<Error> {
    use ErrorCategory::*;
    use schemars::schema::{InstanceType, Schema, SingleOrVec};
    let error = |category, found: &Value, cause: &str, path: &str| {
        Error::new(category, found.clone(), cause).at(path, item)
    };
    if let Some(reference) = &schema.reference {
        let name = reference.trim_start_matches("#/definitions/");
        if let Some(kind) = ScalarKind::parse(name)
            && let Some(text) = value.as_str()
            && let Err(failure) = validate_typed_scalar(kind, text)
        {
            return vec![failure.at(path, item)];
        }
        return definitions.get(name).map_or_else(
            || {
                vec![error(
                    TypeMismatch,
                    value,
                    "a resolvable schema reference",
                    path,
                )]
            },
            |target| walk_target(value, target, definitions, path, item),
        );
    }
    if let Some(choices) = schema
        .subschemas
        .as_ref()
        .and_then(|node| node.any_of.as_ref())
        && let Some(choice) = choices.iter().find(|choice| {
            let is_null = match choice {
                Schema::Object(object) => object
                    .instance_type
                    .as_ref()
                    .is_some_and(|types| types.contains(&InstanceType::Null)),
                Schema::Bool(_) => false,
            };
            is_null == value.is_null()
        })
    {
        return walk_target(value, choice, definitions, path, item);
    }
    let types: Vec<_> = match &schema.instance_type {
        Some(SingleOrVec::Single(kind)) => vec![kind.as_ref()],
        Some(SingleOrVec::Vec(kinds)) => kinds.iter().collect(),
        None => Vec::new(),
    };
    let kind_name = |kind: &InstanceType| match kind {
        InstanceType::Null => "null",
        InstanceType::Boolean => "boolean",
        InstanceType::Object => "object",
        InstanceType::Array => "array",
        InstanceType::Number => "number",
        InstanceType::String => "string",
        InstanceType::Integer => "integer",
    };
    let actual = match value {
        Value::Null => "null",
        Value::Bool(_) => "boolean",
        Value::Number(_) => "number",
        Value::String(_) => "string",
        Value::Array(_) => "array",
        Value::Object(_) => "object",
    };
    if !types.is_empty() && !types.iter().any(|kind| kind_name(kind) == actual) {
        let category = if value.is_null() {
            NullNotAllowed
        } else {
            TypeMismatch
        };
        return vec![error(
            category,
            value,
            &types
                .iter()
                .map(|kind| kind_name(kind))
                .collect::<Vec<_>>()
                .join(" or "),
            path,
        )];
    }
    if let Some(choices) = &schema.enum_values
        && !choices.contains(value)
    {
        let mut error = error(UnknownVariant, value, &json!(choices).to_string(), path);
        error.set_allowed_values(choices.clone());
        return vec![error];
    }
    let mut errors = Vec::new();
    if let (Some(object), Some(specification)) = (value.as_object(), schema.object.as_ref()) {
        errors.extend(walk_object(
            object,
            &specification.properties,
            definitions,
            path,
            item,
        ));
    }
    if let (Some(items), Some(SingleOrVec::Single(specification))) = (
        value.as_array(),
        schema.array.as_ref().and_then(|array| array.items.as_ref()),
    ) {
        errors.extend(walk_array(items, specification, definitions, path));
    }
    errors
}

fn check_record(
    record: &Value,
    schema: &schemars::schema::RootSchema,
    fields: &[emit::FieldMeta],
) -> Vec<Error> {
    let mut errors = walk(record, &schema.schema, &schema.definitions, "", None);
    let record_kind = record.get("id").and_then(Value::as_str).and_then(|text| {
        Id::try_from(text.to_owned())
            .ok()
            .map(|id| id.kind())
            .or_else(|| RecordKind::from_id(text))
    });
    for field in fields.iter().filter(|field| field.supersession) {
        if let Some(target) = record.get(field.name).and_then(Value::as_str)
            && let Some((source_kind, target_kind)) = record_kind.zip(
                Id::try_from(target.to_owned())
                    .ok()
                    .map(|id| id.kind())
                    .or_else(|| RecordKind::from_id(target)),
            )
            && let Some(error) = crate::inventory::cross_kind(
                source_kind,
                target_kind,
                target,
                &format!("/{}", field.name),
            )
        {
            errors.push(error);
        }
    }
    errors
}

fn decode_record(
    kind: TableId,
    record: &Value,
    position: usize,
    batch: &mut Batch,
) -> Result<(), serde_json::Error> {
    match kind {
        TableId::Req => {
            Requirement::deserialize(record).map(|row| batch.add_requirement(position, row))
        }
        TableId::Dec => Decision::deserialize(record).map(|row| batch.add_decision(position, row)),
    }
}

pub fn accept(input: &str) -> Accepted {
    use ErrorCategory::*;
    let mut accepted = Accepted {
        batch: Batch::new(),
        errors: Vec::new(),
    };
    let input: Value = match serde_json::from_str(input) {
        Ok(input) => input,
        Err(error) => {
            accepted
                .errors
                .push(Error::from_serde(json!(input), "a JSON batch input", error));
            return accepted;
        }
    };
    let shape = input.as_object().filter(|object| {
        object.len() == TableId::ALL.len()
            && TableId::ALL
                .iter()
                .all(|table| object.get(table.name()).is_some_and(Value::is_array))
    });
    let Some(object) = shape else {
        let unknown = input.as_object().is_some_and(|object| {
            object
                .keys()
                .any(|key| !TableId::ALL.iter().any(|table| key == table.name()))
        });
        let category = if unknown { UnknownKey } else { TypeMismatch };
        accepted.errors.push(Error::new(
            category,
            input,
            "the two arrays requirements and decisions",
        ));
        return accepted;
    };
    static REQUIREMENTS: OnceLock<schemars::schema::RootSchema> = OnceLock::new();
    static DECISIONS: OnceLock<schemars::schema::RootSchema> = OnceLock::new();
    static REQUIREMENT_FIELDS: OnceLock<Vec<emit::FieldMeta>> = OnceLock::new();
    static DECISION_FIELDS: OnceLock<Vec<emit::FieldMeta>> = OnceLock::new();
    for kind in TableId::ALL {
        let table = kind.name();
        let cache = match kind {
            TableId::Req => &REQUIREMENTS,
            TableId::Dec => &DECISIONS,
        };
        let schema = cache.get_or_init(|| emit::table_schema(kind));
        let field_cache = match kind {
            TableId::Req => &REQUIREMENT_FIELDS,
            TableId::Dec => &DECISION_FIELDS,
        };
        let fields = field_cache.get_or_init(|| emit::field_table(kind));
        for (position, record) in object
            .get(table)
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
            .enumerate()
        {
            let mut errors = check_record(record, schema, fields);
            if errors.is_empty()
                && let Err(error) = decode_record(kind, record, position, &mut accepted.batch)
            {
                errors.push(Error::from_serde(
                    record.clone(),
                    &format!("a valid {table} record"),
                    error,
                ));
            }
            for error in &mut errors {
                error.table = Some(kind);
                error.record_position = Some(RecordPosition(position));
            }
            accepted.errors.extend(errors);
        }
    }
    accepted
        .errors
        .extend(crate::inventory::check_inventory(&accepted.batch));
    accepted
}
