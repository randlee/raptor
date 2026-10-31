use crate::error::{Error, ErrorCategory};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

macro_rules! scalar {
    ($name:ident) => {
        #[derive(
            Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize, JsonSchema,
        )]
        #[serde(try_from = "String")]
        pub struct $name(String);
        impl $name {
            pub fn as_str(&self) -> &str {
                &self.0
            }
        }
        impl AsRef<str> for $name {
            fn as_ref(&self) -> &str {
                self.as_str()
            }
        }
        impl std::fmt::Display for $name {
            fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                formatter.write_str(self.as_str())
            }
        }
        impl TryFrom<String> for $name {
            type Error = Error;
            fn try_from(text: String) -> Result<Self, Error> {
                validate_typed_scalar(ScalarKind::$name, &text)?;
                Ok(Self(text))
            }
        }
    };
}
/// A validated identifier and its cached record kind.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(try_from = "String", into = "String")]
pub struct Id {
    text: String,
    kind: RecordKind,
}
impl JsonSchema for Id {
    fn schema_name() -> String {
        "Id".to_owned()
    }
    fn json_schema(generator: &mut schemars::r#gen::SchemaGenerator) -> schemars::schema::Schema {
        <String as JsonSchema>::json_schema(generator)
    }
}
impl Id {
    pub fn as_str(&self) -> &str {
        &self.text
    }
    pub fn kind(&self) -> RecordKind {
        self.kind
    }
}
impl AsRef<str> for Id {
    fn as_ref(&self) -> &str {
        self.as_str()
    }
}
impl std::fmt::Display for Id {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(self.as_str())
    }
}
impl TryFrom<String> for Id {
    type Error = Error;
    fn try_from(text: String) -> Result<Self, Error> {
        match parse_id(&text) {
            Some(kind) => Ok(Self { text, kind }),
            None => Err(Error::scalar(
                ErrorCategory::InvalidId,
                &text,
                "an ID with REQ, NFR, or ADR prefix and four digits",
            )),
        }
    }
}
impl From<Id> for String {
    fn from(id: Id) -> Self {
        id.text
    }
}
fn parse_id(text: &str) -> Option<RecordKind> {
    let mut parts = text.split('-');
    let (Some(_), Some(project), Some(number), None) =
        (parts.next(), parts.next(), parts.next(), parts.next())
    else {
        return None;
    };
    let kind = RecordKind::from_id(text)?;
    ((2..=5).contains(&project.len())
        && project.bytes().all(|byte| byte.is_ascii_uppercase())
        && number.len() == 4
        && number.bytes().all(|byte| byte.is_ascii_digit()))
    .then_some(kind)
}
scalar!(Version);
scalar!(Date);
#[derive(Clone, Copy)]
pub(crate) enum ScalarKind {
    Id,
    Version,
    Date,
}
impl ScalarKind {
    pub(crate) fn parse(name: &str) -> Option<Self> {
        match name {
            "Id" => Some(Self::Id),
            "Version" => Some(Self::Version),
            "Date" => Some(Self::Date),
            _ => None,
        }
    }
}
pub fn validate_scalar(kind: &str, text: &str) -> Result<(), Error> {
    match ScalarKind::parse(kind) {
        Some(kind) => validate_typed_scalar(kind, text),
        None => Err(Error::scalar(
            ErrorCategory::UnknownVariant,
            text,
            "one of Id, Version, or Date",
        )),
    }
}
pub(crate) fn validate_typed_scalar(kind: ScalarKind, text: &str) -> Result<(), Error> {
    let digits = |part: &str| part.bytes().all(|byte| byte.is_ascii_digit());
    let parts: Vec<_> = text.split('-').collect();
    let valid = match (kind, parts.as_slice()) {
        (ScalarKind::Id, _) => parse_id(text).is_some(),
        (ScalarKind::Version, _) => {
            let components: Vec<_> = text.split('.').collect();
            components.len() == 3
                && components
                    .iter()
                    .all(|part| part.len() == 1 && digits(part))
        }
        (ScalarKind::Date, [year, month, day]) => {
            let leap = year.parse::<u16>().is_ok_and(|year| {
                year.is_multiple_of(4) && (!year.is_multiple_of(100) || year.is_multiple_of(400))
            });
            let end = match *month {
                "02" if leap => 29,
                "02" => 28,
                "04" | "06" | "09" | "11" => 30,
                "01" | "03" | "05" | "07" | "08" | "10" | "12" => 31,
                _ => 0,
            };
            year.len() == 4
                && digits(year)
                && day.len() == 2
                && digits(day)
                && day.parse::<u8>().is_ok_and(|day| (1..=end).contains(&day))
        }
        _ => false,
    };
    if valid {
        return Ok(());
    }
    let (category, cause) = match kind {
        ScalarKind::Id => (
            ErrorCategory::InvalidId,
            "an ID with REQ, NFR, or ADR prefix and four digits",
        ),
        ScalarKind::Version => (ErrorCategory::InvalidVersion, "a version in N.N.N format"),
        ScalarKind::Date => (ErrorCategory::InvalidDate, "a valid YYYY-MM-DD date"),
    };
    Err(Error::scalar(category, text, cause))
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub enum Status {
    Draft,
    Proposed,
    Active,
    Approved,
    Deprecated,
    Superseded,
}

#[derive(
    Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize, JsonSchema,
)]
pub enum RecordKind {
    Req,
    Nfr,
    Adr,
}

impl RecordKind {
    pub fn from_id(value: &str) -> Option<Self> {
        match value.split_once('-')?.0 {
            "REQ" => Some(Self::Req),
            "NFR" => Some(Self::Nfr),
            "ADR" => Some(Self::Adr),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub enum Modal {
    Must,
    Should,
    MustNot,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
pub struct Identity {
    pub id: Id,
    pub title: String,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
pub struct Lifecycle {
    pub status: Status,
    pub version: Version,
    pub created: Date,
    pub last_updated: Date,
    pub owner: String,
    pub supersedes: Option<Id>,
    pub superseded_by: Option<Id>,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Statement {
    pub modal: Modal,
    pub text: String,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct CheckItem {
    pub text: String,
    pub checked: Option<bool>,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct IdItem {
    pub id: Id,
    pub note: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct LinkItem {
    pub text: String,
    pub href: String,
    pub note: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct RelatedDocuments {
    pub text: String,
    pub requirements: Vec<IdItem>,
    pub architecture_decisions: Vec<IdItem>,
    pub design_documents: Vec<LinkItem>,
    pub work_items: Vec<LinkItem>,
    pub external_references: Vec<LinkItem>,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct RequirementStatement {
    pub text: String,
    pub statements: Vec<Statement>,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct SuccessCriteria {
    pub text: String,
    pub acceptance_criteria: Vec<CheckItem>,
    pub test_evidence: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Dependencies {
    pub text: String,
    pub requires: Vec<IdItem>,
    pub related: Vec<IdItem>,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ProductApplicability {
    pub text: String,
    pub applies_to: Vec<String>,
    pub does_not_apply_to: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ImplementationNotes {
    pub text: String,
    pub key_considerations: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct TestStrategy {
    pub text: String,
    pub test_types: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Alternative {
    pub name: String,
    pub description: String,
    pub pros: Vec<String>,
    pub cons: Vec<String>,
    pub why_rejected: String,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Alternatives {
    pub text: String,
    pub groups: Vec<Alternative>,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Context {
    pub text: String,
    pub background: String,
    pub problem_statement: String,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct DecisionSection {
    pub text: String,
    pub chosen_approach: String,
    pub key_principles: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct DecisionRationale {
    pub text: String,
    pub benefits: Vec<String>,
    pub trade_offs: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Consequences {
    pub text: String,
    pub positive: Vec<String>,
    pub negative: Vec<String>,
    pub neutral: Vec<String>,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Implementation {
    pub text: String,
    pub key_components: Vec<String>,
    pub integration_points: Vec<String>,
    pub code_examples: String,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ImpactAnalysis {
    pub text: String,
    pub affected_components: String,
    pub performance_impact: String,
    pub security_impact: String,
    pub maintainability_impact: String,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
pub struct Requirement {
    #[serde(flatten)]
    pub identity: Identity,
    #[serde(flatten)]
    pub lifecycle: Lifecycle,
    pub requirement_statement: RequirementStatement,
    pub rationale: String,
    pub success_criteria: SuccessCriteria,
    pub dependencies: Dependencies,
    pub product_applicability: ProductApplicability,
    pub implementation_notes: ImplementationNotes,
    pub test_strategy: TestStrategy,
    pub related_documents: RelatedDocuments,
}

#[derive(Debug, Serialize, Deserialize, JsonSchema)]
pub struct Decision {
    #[serde(flatten)]
    pub identity: Identity,
    #[serde(flatten)]
    pub lifecycle: Lifecycle,
    pub decision_date: Date,
    pub context: Context,
    pub decision: DecisionSection,
    pub rationale: DecisionRationale,
    pub consequences: Consequences,
    pub alternatives: Alternatives,
    pub implementation: Implementation,
    pub impact_analysis: ImpactAnalysis,
    pub related_documents: RelatedDocuments,
}
