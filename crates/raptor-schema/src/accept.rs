use crate::{emit, schema::*};
use serde::{Serialize, Serializer};
use serde_json::{Value, json};
use std::fmt;

#[derive(Clone, Debug, Serialize)]
pub enum ErrorCategory {
    UnknownKey,
    MissingKey,
    TypeMismatch,
    NullNotAllowed,
    InvalidId,
    InvalidVersion,
    InvalidDate,
    UnknownVariant,
    CrossKindSupersession,
    DuplicateId,
    DanglingReference,
}

#[derive(Clone, Debug, Serialize)]
pub struct Error {
    pub category: ErrorCategory,
    pub table: Option<Box<str>>,
    pub record_position: Option<usize>,
    pub field_path: Box<str>,
    pub item_index: Option<usize>,
    pub offending_value: Box<Value>,
    pub cause: Box<str>,
    pub message: Box<str>,
}
impl Error {
    pub fn scalar(category: ErrorCategory, text: &str) -> Self {
        Self::new(category, json!(text), "value does not satisfy the scalar format")
    }
    pub fn new(category: ErrorCategory, value: Value, cause: &str) -> Self {
        Self {
            message: format!("Found {value}; expected {cause}.").into(),
            category,
            offending_value: Box::new(value),
            cause: cause.into(),
            table: None,
            record_position: None,
            field_path: Box::default(),
            item_index: None,
        }
    }
    pub fn at(mut self, path: &str, item: Option<usize>) -> Self {
        self.field_path = path.into();
        self.item_index = item;
        self
    }
}
impl fmt::Display for Error {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.message)
    }
}
impl std::error::Error for Error {}

#[derive(Debug, Serialize)]
pub struct Batch {
    #[serde(serialize_with = "unpositioned")]
    requirements: Vec<(usize, Requirement)>,
    #[serde(serialize_with = "unpositioned")]
    decisions: Vec<(usize, Decision)>,
}
fn unpositioned<T: Serialize, S: Serializer>(
    rows: &[(usize, T)],
    serializer: S,
) -> Result<S::Ok, S::Error> {
    serializer.collect_seq(rows.iter().map(|(_, row)| row))
}
impl Batch {
    pub fn requirements(&self) -> impl Iterator<Item = (usize, &Requirement)> {
        self.requirements
            .iter()
            .map(|(position, row)| (*position, row))
    }
    pub fn decisions(&self) -> impl Iterator<Item = (usize, &Decision)> {
        self.decisions
            .iter()
            .map(|(position, row)| (*position, row))
    }
}
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

fn walk(
    value: &Value,
    schema: &Value,
    definitions: &Value,
    path: &str,
    item: Option<usize>,
) -> Vec<Error> {
    use ErrorCategory::*;
    let error = |category, found: &Value, cause: &str, path: &str| {
        Error::new(category, found.clone(), cause).at(path, item)
    };
    if let Some(reference) = schema.get("$ref").and_then(Value::as_str) {
        let name = reference.trim_start_matches("#/definitions/");
        if matches!(name, "Id" | "Version" | "Date")
            && let Some(text) = value.as_str()
            && let Err(failure) = validate_scalar(name, text)
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
            |target| walk(value, target, definitions, path, item),
        );
    }
    if let Some(choices) = schema.get("anyOf").and_then(Value::as_array)
        && let Some(choice) = choices.iter().find(|choice| {
            (choice.get("type").and_then(Value::as_str) == Some("null")) == value.is_null()
        })
    {
        return walk(value, choice, definitions, path, item);
    }
    let types: Vec<_> = match schema.get("type") {
        Some(Value::String(kind)) => vec![kind.as_str()],
        Some(Value::Array(types)) => types.iter().filter_map(Value::as_str).collect(),
        _ => Vec::new(),
    };
    let actual = match value {
        Value::Null => "null",
        Value::Bool(_) => "boolean",
        Value::Number(_) => "number",
        Value::String(_) => "string",
        Value::Array(_) => "array",
        Value::Object(_) => "object",
    };
    if !types.is_empty() && !types.contains(&actual) {
        let category = if value.is_null() {
            NullNotAllowed
        } else {
            TypeMismatch
        };
        return vec![error(category, value, &types.join(" or "), path)];
    }
    if let Some(choices) = schema.get("enum").and_then(Value::as_array)
        && !choices.contains(value)
    {
        return vec![error(
            UnknownVariant,
            value,
            &json!(choices).to_string(),
            path,
        )];
    }
    let mut errors = Vec::new();
    if let (Some(object), Some(properties)) =
        (value.as_object(), schema.get("properties").and_then(Value::as_object))
    {
        for (name, found) in object
            .iter()
            .filter(|(name, _)| !properties.contains_key(*name))
        {
            errors.push(error(UnknownKey, found, "a declared key", &format!("{path}/{name}")));
        }
        for (name, specification) in properties {
            let field_path = format!("{path}/{name}");
            if let Some(found) = object.get(name) {
                errors.extend(walk(found, specification, definitions, &field_path, item));
            } else {
                errors.push(error(MissingKey, &Value::Null, "an explicit key", &field_path));
            }
        }
    }
    if let (Some(items), Some(specification)) = (value.as_array(), schema.get("items")) {
        for (index, found) in items.iter().enumerate() {
            errors.extend(walk(
                found,
                specification,
                definitions,
                &format!("{path}/{index}"),
                Some(index),
            ));
        }
    }
    errors
}

pub fn accept(input: &str) -> Accepted {
    use ErrorCategory::*;
    let mut accepted = Accepted {
        batch: Batch {
            requirements: Vec::new(),
            decisions: Vec::new(),
        },
        errors: Vec::new(),
    };
    let input: Value = match serde_json::from_str(input) {
        Ok(input) => input,
        Err(error) => {
            accepted
                .errors
                .push(Error::new(TypeMismatch, json!(input), &error.to_string()));
            return accepted;
        }
    };
    let shape = input.as_object().filter(|object| {
        object.len() == emit::TABLES.len()
            && emit::TABLES
                .iter()
                .all(|(table, _)| object.get(*table).is_some_and(Value::is_array))
    });
    let Some(object) = shape else {
        let unknown = input.as_object().is_some_and(|object| {
            object
                .keys()
                .any(|key| !emit::TABLES.iter().any(|(table, _)| key == table))
        });
        let category = if unknown { UnknownKey } else { TypeMismatch };
        accepted.errors.push(Error::new(
            category,
            input,
            "the two arrays requirements and decisions",
        ));
        return accepted;
    };
    let schemas = match emit::json_schema().and_then(serde_json::to_value) {
        Ok(schemas) => schemas,
        Err(error) => {
            accepted
                .errors
                .push(Error::new(TypeMismatch, Value::Null, &error.to_string()));
            return accepted;
        }
    };
    for (table, kind) in emit::TABLES {
        let Some(schema) = schemas.get(table) else {
            continue;
        };
        let definitions = schema.get("definitions").cloned().unwrap_or_default();
        for (position, record) in object
            .get(table)
            .and_then(Value::as_array)
            .into_iter()
            .flatten()
            .enumerate()
        {
            let mut errors = walk(record, schema, &definitions, "", None);
            let fields = emit::field_table(kind);
            for field in fields.iter().filter(|field| field.nullable) {
                if let (Some(id), Some(target)) = (
                    record.get("id").and_then(Value::as_str),
                    record.get(field.name).and_then(Value::as_str),
                ) && id.split('-').next() != target.split('-').next()
                {
                    errors.push(
                        Error::new(
                            CrossKindSupersession,
                            json!(target),
                            "an identifier of the same kind",
                        )
                        .at(&format!("/{}", field.name), None),
                    );
                }
            }
            if errors.is_empty() {
                let decoded = match kind {
                    Table::Req => serde_json::from_value(record.clone())
                        .map(|row| accepted.batch.requirements.push((position, row))),
                    Table::Dec => serde_json::from_value(record.clone())
                        .map(|row| accepted.batch.decisions.push((position, row))),
                    Table::Both => continue,
                };
                if let Err(error) = decoded {
                    errors.push(Error::new(TypeMismatch, record.clone(), &error.to_string()));
                }
            }
            for error in &mut errors {
                error.table = Some(table.into());
                error.record_position = Some(position);
            }
            accepted.errors.extend(errors);
        }
    }
    accepted
        .errors
        .extend(crate::inventory::check_inventory(&accepted.batch));
    accepted
}
