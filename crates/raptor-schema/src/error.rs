use serde::{Serialize, Serializer, ser::SerializeStruct};
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

impl ErrorCategory {
    pub const ALL: [Self; 11] = [
        Self::UnknownKey,
        Self::MissingKey,
        Self::TypeMismatch,
        Self::NullNotAllowed,
        Self::InvalidId,
        Self::InvalidVersion,
        Self::InvalidDate,
        Self::UnknownVariant,
        Self::CrossKindSupersession,
        Self::DuplicateId,
        Self::DanglingReference,
    ];
}

/// A zero-based record position in the original input table.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(transparent)]
pub struct RecordPosition(pub usize);

/// A zero-based item position in an array.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(transparent)]
pub struct ItemIndex(pub usize);

#[derive(Clone, Debug, Default, PartialEq)]
struct ErrorDetail {
    item_index: Option<ItemIndex>,
    allowed_values: Option<Box<[Value]>>,
    first_occurrence_record_position: Option<RecordPosition>,
}

/// Describes a rejected value, its location, and how to correct it.
///
/// Rare diagnostic details share one allocation to keep this error small when
/// returned by value, while common scalar errors do not allocate that detail.
#[derive(Clone, Debug, PartialEq)]
pub struct Error {
    /// The reason this value was rejected.
    pub category: ErrorCategory,
    /// The containing table, or None for a batch-level error.
    pub table: Option<TableId>,
    /// Zero-based record position in the original table, before rejection filtering.
    pub record_position: Option<RecordPosition>,
    /// JSON pointer to the invalid field, or empty for a root error.
    pub field_path: Box<str>,
    /// The original JSON value that failed validation.
    pub offending_value: Box<Value>,
    /// The expected shape or constraint, including any original serde detail.
    pub cause: Box<str>,
    /// The complete human-readable diagnostic.
    pub message: Box<str>,
    /// An action the caller can take to correct this category of error.
    pub recovery: &'static str,
    details: Option<Box<ErrorDetail>>,
}
/// Identifies exactly one table containing a rejected record.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize)]
pub enum TableId {
    /// The requirements table, including nonfunctional requirements.
    #[serde(rename = "requirements")]
    Req,
    /// The architecture decisions table.
    #[serde(rename = "decisions")]
    Dec,
}
impl TableId {
    pub const ALL: [Self; 2] = [Self::Req, Self::Dec];
    pub const fn name(self) -> &'static str {
        match self {
            Self::Req => "requirements",
            Self::Dec => "decisions",
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
            details: None,
        }
    }
    /// Index of the offending array item, if any.
    pub fn item_index(&self) -> Option<ItemIndex> {
        self.details.as_ref().and_then(|detail| detail.item_index)
    }
    /// Permitted choices, when the error reports an unknown variant.
    pub fn allowed_values(&self) -> Option<&[Value]> {
        self.details
            .as_ref()
            .and_then(|detail| detail.allowed_values.as_deref())
    }
    /// Position of the first occurrence of a duplicate identifier.
    pub fn first_occurrence_record_position(&self) -> Option<RecordPosition> {
        self.details
            .as_ref()
            .and_then(|detail| detail.first_occurrence_record_position)
    }
    pub(crate) fn set_allowed_values(&mut self, values: Vec<Value>) {
        self.details
            .get_or_insert_with(Default::default)
            .allowed_values = Some(values.into_boxed_slice());
    }
    pub(crate) fn set_first_occurrence(&mut self, position: RecordPosition) {
        self.details
            .get_or_insert_with(Default::default)
            .first_occurrence_record_position = Some(position);
    }
    /// Reports a serialization failure without requiring callers to construct JSON values.
    pub fn serialization(expected: &str, error: serde_json::Error) -> Self {
        Self::from_serde(Value::Null, expected, error)
    }
    /// Adapts a serde failure to the shared error constructor, preserving its detail.
    pub fn from_serde(value: Value, expected: &str, error: serde_json::Error) -> Self {
        Self::new(
            ErrorCategory::TypeMismatch,
            value,
            &format!("{expected} ({error})"),
        )
    }
    pub fn at(mut self, path: &str, item: Option<ItemIndex>) -> Self {
        self.field_path = path.into();
        if let Some(item) = item {
            self.details.get_or_insert_with(Default::default).item_index = Some(item);
        }
        self
    }
}
impl Serialize for Error {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        let mut output = serializer.serialize_struct("Error", 11)?;
        output.serialize_field("category", &self.category)?;
        output.serialize_field("table", &self.table)?;
        output.serialize_field("record_position", &self.record_position)?;
        output.serialize_field("field_path", &self.field_path)?;
        output.serialize_field("item_index", &self.item_index())?;
        output.serialize_field("offending_value", &self.offending_value)?;
        output.serialize_field("cause", &self.cause)?;
        output.serialize_field("message", &self.message)?;
        output.serialize_field("recovery", &self.recovery)?;
        output.serialize_field("allowed_values", &self.allowed_values())?;
        output.serialize_field(
            "first_occurrence_record_position",
            &self.first_occurrence_record_position(),
        )?;
        output.end()
    }
}
impl fmt::Display for Error {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(&self.message)
    }
}
impl std::error::Error for Error {}
