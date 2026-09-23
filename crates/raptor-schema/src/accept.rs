use crate::{emit, schema::*};
use serde::{Serialize, Serializer};
use serde_json::{Value, json};
use std::fmt;

/// Classifies why input could not be accepted into the batch.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize)]
pub enum ErrorCategory {
    /// An object contains a key not declared by its schema.
    UnknownKey,
    /// An object omits a required key.
    MissingKey,
    /// A value or batch has the wrong JSON shape or cannot be decoded.
    TypeMismatch,
    /// A non-nullable field contains JSON null.
    NullNotAllowed,
    /// An identifier does not match the supported record ID format.
    InvalidId,
    /// A version does not match the supported version format.
    InvalidVersion,
    /// A date has an invalid format or calendar value.
    InvalidDate,
    /// A value is outside the permitted choices.
    UnknownVariant,
    /// A supersession link connects different record kinds.
    CrossKindSupersession,
    /// Multiple accepted records share an identifier.
    DuplicateId,
    /// A reference has no matching accepted record in the batch.
    DanglingReference,
}

/// Describes a rejected value, its location, and how to correct it.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct Error {
    /// The reason this value was rejected.
    pub category: ErrorCategory,
    /// The containing table, or None for a batch-level error.
    pub table: Option<ErrorTable>,
    /// Zero-based record position in the original table, before rejection filtering.
    pub record_position: Option<usize>,
    /// JSON pointer to the invalid field, or empty for a root error.
    pub field_path: Box<str>,
    // Boxing here and below is a size choice, not a semantic distinction from record_position.
    // This set keeps size_of::<Error>() below result_large_err's 128-byte limit.
    /// Zero-based position of an invalid array item, if applicable.
    pub item_index: Option<Box<usize>>,
    /// The original JSON value that failed validation.
    pub offending_value: Box<Value>,
    /// The expected shape or constraint, including any original serde detail.
    pub cause: Box<str>,
    /// The complete human-readable diagnostic.
    pub message: Box<str>,
    /// An action the caller can take to correct this category of error.
    pub recovery: &'static str,
    /// Allowed values for `UnknownVariant`; otherwise `None`.
    pub allowed_values: Option<Box<Vec<Value>>>,
    /// First duplicate position for `DuplicateId`; otherwise `None`.
    pub first_occurrence_record_position: Option<Box<usize>>,
}
/// Identifies exactly one table containing a rejected record.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize)]
pub enum ErrorTable {
    /// The requirements table, including nonfunctional requirements.
    #[serde(rename = "requirements")]
    Req,
    /// The architecture decisions table.
    #[serde(rename = "decisions")]
    Dec,
}
impl TryFrom<Table> for ErrorTable {
    type Error = &'static str;
    fn try_from(table: Table) -> Result<Self, Self::Error> {
        match table {
            Table::Req => Ok(Self::Req),
            Table::Dec => Ok(Self::Dec),
            Table::Both => Err("a single requirements or decisions table"),
        }
    }
}
fn recovery(category: &ErrorCategory) -> &'static str {
    use ErrorCategory::*;
    match category {
        UnknownKey => "Remove the undeclared key or use a declared key.",
        MissingKey => "Add the required key at the reported field path.",
        TypeMismatch => "Replace the value with the expected JSON type.",
        NullNotAllowed => "Replace null with a value of the expected JSON type.",
        InvalidId | InvalidVersion => "Replace the value with the expected format.",
        InvalidDate => "Replace the date with a valid date in the expected format.",
        UnknownVariant => "Replace the value with one of the allowed values.",
        CrossKindSupersession => "Reference an identifier of the same record kind.",
        DuplicateId => "Rename one record so each identifier is unique.",
        DanglingReference => "Create the referenced record or correct the reference.",
    }
}
impl Error {
    /// Creates an error for a scalar value using its expected format.
    pub fn scalar(category: ErrorCategory, text: &str, cause: &str) -> Self {
        Self::new(category, json!(text), cause)
    }
    /// Creates an error with its category, offending value, and expectation.
    pub fn new(category: ErrorCategory, value: Value, cause: &str) -> Self {
        Self {
            message: format!("Found {value}; expected {cause}.").into(),
            recovery: recovery(&category),
            category,
            offending_value: Box::new(value),
            cause: cause.into(),
            table: None,
            record_position: None,
            field_path: Box::default(),
            item_index: None,
            allowed_values: None,
            first_occurrence_record_position: None,
        }
    }
    /// Adapts a serde failure to the shared error constructor, preserving its detail.
    pub fn from_serde(value: Value, expected: &str, error: serde_json::Error) -> Self {
        Self::new(ErrorCategory::TypeMismatch, value, &format!("{expected} ({error})"))
    }
    pub fn at(mut self, path: &str, item: Option<usize>) -> Self {
        self.field_path = path.into();
        self.item_index = item.map(Box::new);
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
        let mut error = error(UnknownVariant, value, &json!(choices).to_string(), path);
        error.allowed_values = Some(Box::new(choices.clone()));
        return vec![error];
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
                .push(Error::from_serde(json!(input), "a JSON batch input", error));
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
            accepted.errors.push(Error::from_serde(
                Value::Null,
                "a serializable schema definition",
                error,
            ));
            return accepted;
        }
    };
    for (table, kind) in emit::TABLES {
        let error_table = match ErrorTable::try_from(kind) {
            Ok(table) => table,
            Err(cause) => {
                accepted
                    .errors
                    .push(Error::new(UnknownVariant, json!(table), cause));
                return accepted;
            }
        };
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
            let record_kind = record
                .get("id")
                .and_then(Value::as_str)
                .and_then(RecordKind::from_id);
            for field in fields.iter().filter(|field| field.nullable) {
                if let Some(target) = record.get(field.name).and_then(Value::as_str)
                    && let Some((source_kind, target_kind)) =
                        record_kind.zip(RecordKind::from_id(target))
                    && source_kind != target_kind
                {
                    errors.push(
                        Error::new(
                            CrossKindSupersession,
                            json!(target),
                            &format!("a {source_kind:?} identifier, not {target_kind:?}"),
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
                    errors.push(Error::from_serde(
                        record.clone(),
                        &format!("a valid {table} record"),
                        error,
                    ));
                }
            }
            for error in &mut errors {
                error.table = Some(error_table);
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
