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
        ("Id", ["REQ" | "NFR" | "ADR", project, number]) => {
            (2..=5).contains(&project.len())
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
    let category = match kind {
        "Id" => ErrorCategory::InvalidId,
        "Version" => ErrorCategory::InvalidVersion,
        "Date" => ErrorCategory::InvalidDate,
        _ => ErrorCategory::UnknownVariant,
    };
    Err(Error::scalar(category, text))
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

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Table {
    Req,
    Dec,
    Both,
}
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Presence {
    Required,
    Optional,
    Nullable,
}
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Level {
    Header,
    Item,
    Section,
    Label(Section),
}
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Shape {
    Text,
    Date,
    Version,
    Status,
    Id,
    IdList,
    TextList,
    StatementList,
    Statements(Modal),
    Checklist,
    LinkList,
    Group,
    Derived,
}
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Section {
    Statement,
    Rationale,
    Success,
    Dependencies,
    Product,
    ImplNotes,
    Test,
    Related,
    Context,
    Decision,
    Consequences,
    Alternatives,
    Implementation,
    Impact,
}
impl Section {
    pub fn heading(self) -> &'static str {
        match self {
            Self::Statement => "Requirement Statement",
            Self::Rationale => "Rationale",
            Self::Success => "Success Criteria",
            Self::Dependencies => "Dependencies",
            Self::Product => "Product Applicability",
            Self::ImplNotes => "Implementation Notes",
            Self::Test => "Test Strategy",
            Self::Related => "Related Documents",
            Self::Context => "Context",
            Self::Decision => "Decision",
            Self::Consequences => "Consequences",
            Self::Alternatives => "Alternatives Considered",
            Self::Implementation => "Implementation",
            Self::Impact => "Impact Analysis",
        }
    }
}
pub type Field = (&'static str, &'static str, Table, Level, Shape, Presence);
use self::Section as S;
use Level::{Header, Item, Label, Section as SectionLevel};
use Modal::*;
use Presence::*;
use Shape::{
    Checklist, Derived, Group, IdList, LinkList, StatementList, Statements, Text, TextList,
};
use Table::*;
pub const FIELDS: &[Field] = &[
    ("integration_points", "Integration Points", Dec, Label(S::Implementation), TextList, Optional),
    ("architecture_decisions", "Architecture Decisions", Both, Label(S::Related), IdList, Optional),
    ("statements", "MUST NOT statements", Req, Label(S::Statement), Statements(MustNot), Optional),
    ("statements", "SHOULD statements", Req, Label(S::Statement), Statements(Should), Optional),
    ("maintainability_impact", "Maintainability Impact", Dec, Label(S::Impact), Text, Optional),
    ("external_references", "External References", Both, Label(S::Related), LinkList, Optional),
    ("acceptance_criteria", "Acceptance Criteria", Req, Label(S::Success), Checklist, Optional),
    ("key_considerations", "Key Considerations", Req, Label(S::ImplNotes), TextList, Optional),
    ("requirement_statement", "Requirement Statement", Req, SectionLevel, StatementList, Required),
    ("statements", "MUST statements", Req, Label(S::Statement), Statements(Must), Optional),
    ("product_applicability", "Product Applicability", Req, SectionLevel, TextList, Optional),
    ("key_components", "Key Components", Dec, Label(S::Implementation), TextList, Optional),
    ("does_not_apply_to", "Does Not Apply To", Req, Label(S::Product), TextList, Optional),
    ("implementation_notes", "Implementation Notes", Req, SectionLevel, TextList, Optional),
    ("design_documents", "Design Documents", Both, Label(S::Related), LinkList, Optional),
    ("affected_components", "Affected Components", Dec, Label(S::Impact), Text, Optional),
    ("performance_impact", "Performance Impact", Dec, Label(S::Impact), Text, Optional),
    ("problem_statement", "Problem Statement", Dec, Label(S::Context), Text, Optional),
    ("key_principles", "Key Principles", Dec, Label(S::Decision), TextList, Optional),
    ("code_examples", "Code Examples", Dec, Label(S::Implementation), Text, Optional),
    ("chosen_approach", "Chosen Approach", Dec, Label(S::Decision), Text, Optional),
    ("test_evidence", "Test Evidence", Req, Label(S::Success), TextList, Optional),
    ("success_criteria", "Success Criteria", Req, SectionLevel, Checklist, Required),
    ("why_rejected", "Why Rejected", Dec, Label(S::Alternatives), Text, Optional),
    ("security_impact", "Security Impact", Dec, Label(S::Impact), Text, Optional),
    ("related_documents", "Related Documents", Both, SectionLevel, Group, Optional),
    ("alternatives", "Alternatives Considered", Dec, SectionLevel, Group, Optional),
    ("trade_offs", "Trade-offs", Both, Label(S::Rationale), TextList, Optional),
    ("requirements", "Requirements", Both, Label(S::Related), IdList, Optional),
    ("description", "Description", Dec, Label(S::Alternatives), Text, Optional),
    ("work_items", "Work Items", Both, Label(S::Related), LinkList, Optional),
    ("positive", "Positive", Dec, Label(S::Consequences), TextList, Optional),
    ("negative", "Negative", Dec, Label(S::Consequences), TextList, Optional),
    ("applies_to", "Applies To", Req, Label(S::Product), TextList, Optional),
    ("test_strategy", "Test Strategy", Req, SectionLevel, TextList, Optional),
    ("requires", "Requires", Req, Label(S::Dependencies), IdList, Optional),
    ("neutral", "Neutral", Dec, Label(S::Consequences), TextList, Optional),
    ("impact_analysis", "Impact Analysis", Dec, SectionLevel, Text, Optional),
    ("benefits", "Benefits", Both, Label(S::Rationale), TextList, Optional),
    ("test_types", "Test Types", Req, Label(S::Test), TextList, Optional),
    ("related", "Related", Req, Label(S::Dependencies), IdList, Optional),
    ("implementation", "Implementation", Dec, SectionLevel, Text, Optional),
    ("background", "Background", Dec, Label(S::Context), Text, Optional),
    ("dependencies", "Dependencies", Req, SectionLevel, IdList, Optional),
    ("decision_date", "Decision Date", Dec, Header, Shape::Date, Required),
    ("superseded_by", "Superseded By", Both, Header, Shape::Id, Nullable),
    ("pros", "Pros", Dec, Label(S::Alternatives), TextList, Optional),
    ("last_updated", "Last Updated", Both, Header, Shape::Date, Required),
    ("consequences", "Consequences", Dec, SectionLevel, Text, Required),
    ("cons", "Cons", Dec, Label(S::Alternatives), TextList, Optional),
    ("id_range", "ID Range", Both, Header, Derived, Optional),
    ("supersedes", "Supersedes", Both, Header, Shape::Id, Nullable),
    ("rationale", "Rationale", Req, SectionLevel, Text, Required),
    ("rationale", "Rationale", Dec, SectionLevel, Text, Required),
    ("version", "Version", Both, Header, Shape::Version, Required),
    ("decision", "Decision", Dec, SectionLevel, Text, Required),
    ("status", "Status", Both, Header, Shape::Status, Required),
    ("created", "Created", Both, Header, Shape::Date, Required),
    ("context", "Context", Dec, SectionLevel, Text, Required),
    ("status", "Status", Both, Item, Shape::Status, Required),
    ("owner", "Owner", Both, Header, Text, Required),
    ("title", "Title", Both, Item, Text, Required),
    ("id", "ID", Both, Item, Shape::Id, Required),
];
