use crate::error::ErrorCategory;
use serde::Serialize;

/// Diagnostic taxonomy shared with the Python source qualifier.
///
/// `MissingId`, `MissingField`, `UnknownSection`, and `UnknownLabel` are
/// source-only rules: the `x-raptor-rules` schema extension exports them for
/// the qualifier, but `ErrorCategory::rule` never returns them. Rust error
/// summaries therefore count only `BadValue`, `DuplicateId`, and
/// `DanglingReference`; the qualifier reports source rules under the same
/// exported boundary contract.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Rule {
    MissingId,
    MissingField,
    UnknownSection,
    UnknownLabel,
    BadValue,
    DuplicateId,
    DanglingReference,
}

impl ErrorCategory {
    pub(crate) fn rule(self) -> Rule {
        match self {
            ErrorCategory::DuplicateId => Rule::DuplicateId,
            ErrorCategory::DanglingReference => Rule::DanglingReference,
            ErrorCategory::UnknownKey
            | ErrorCategory::MissingKey
            | ErrorCategory::TypeMismatch
            | ErrorCategory::NullNotAllowed
            | ErrorCategory::InvalidId
            | ErrorCategory::InvalidDate
            | ErrorCategory::InvalidVersion
            | ErrorCategory::UnknownVariant
            | ErrorCategory::CrossKindSupersession => Rule::BadValue,
        }
    }
}
