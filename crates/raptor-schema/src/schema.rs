use crate::accept::{Error, ErrorCategory};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

macro_rules! scalar {
    ($name:ident) => {
        #[derive(Debug, Serialize, Deserialize, JsonSchema)]
        #[serde(try_from = "String")]
        pub struct $name(String);
        impl $name {
            pub fn as_str(&self) -> &str {
                &self.0
            }
        }
        impl TryFrom<String> for $name {
            type Error = Error;
            fn try_from(text: String) -> Result<Self, Error> {
                validate_scalar(stringify!($name), &text)?;
                Ok(Self(text))
            }
        }
    };
}
scalar!(Id);
scalar!(Version);
scalar!(Date);
pub fn validate_scalar(kind: &str, text: &str) -> Result<(), Error> {
    let digits = |part: &str| part.bytes().all(|byte| byte.is_ascii_digit());
    let parts: Vec<_> = text.split('-').collect();
    let valid = match (kind, parts.as_slice()) {
        ("Id", [_, project, number]) => {
            RecordKind::from_id(text).is_some()
                && (2..=5).contains(&project.len())
                && project.bytes().all(|byte| byte.is_ascii_uppercase())
                && number.len() == 4
                && digits(number)
        }
        ("Version", _) => {
            let components: Vec<_> = text.split('.').collect();
            components.len() == 3
                && components
                    .iter()
                    .all(|part| part.len() == 1 && digits(part))
        }
        ("Date", [year, month, day]) => {
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
        "Id" => (ErrorCategory::InvalidId, "an ID with REQ, NFR, or ADR prefix and four digits"),
        "Version" => (ErrorCategory::InvalidVersion, "a version in N.N.N format"),
        "Date" => (ErrorCategory::InvalidDate, "a valid YYYY-MM-DD date"),
        _ => (ErrorCategory::UnknownVariant, "one of Id, Version, or Date"),
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

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
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
