use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use std::{
    collections::{BTreeMap, HashMap, HashSet},
    str::FromStr,
};
#[rustfmt::skip]
macro_rules! string_type { ($name:ident, $check:expr) => { #[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct $name(pub String); impl FromStr for $name { type Err = String; fn from_str(value: &str) -> Result<Self, Self::Err> { if $check(value) { Ok(Self(value.into())) } else { Err(value.into()) } } } }; }
fn version(value: &str) -> bool {
    let p: Vec<_> = value.split('.').collect();
    p.len() == 3
        && p.iter()
            .all(|x| x.len() == 1 && x.bytes().all(|c| c.is_ascii_digit()))
}
#[rustfmt::skip]
fn date(value: &str) -> bool { let b = value.as_bytes(); if b.len() != 10 || b[4] != b'-' || b[7] != b'-' || !b.iter().enumerate().all(|(i, c)| matches!(i, 4 | 7) || c.is_ascii_digit()) { return false }; let n = |i| (b[i] - b'0') as u16 * 10 + (b[i + 1] - b'0') as u16; let (y, m, d) = (n(0), n(5), n(8)); let days = [31, 28 + u16::from(y % 4 == 0 && (y % 100 != 0 || y % 400 == 0)), 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]; (1..=12).contains(&m) && (1..=days[(m - 1) as usize]).contains(&d) }
fn identifier(value: &str) -> bool {
    let p: Vec<_> = value.split('-').collect();
    matches!(p.first(), Some(&"REQ" | &"NFR" | &"ADR"))
        && p.len() == 3
        && (2..=5).contains(&p[1].len())
        && p[1].bytes().all(|c| c.is_ascii_uppercase())
        && p[2].len() == 4
        && p[2].bytes().all(|c| c.is_ascii_digit())
}
string_type!(Version, version);
string_type!(Date, date);
string_type!(Id, identifier);
#[rustfmt::skip]
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] #[serde(rename_all = "PascalCase")] pub enum Status { Draft, Proposed, Active, Approved, Deprecated, Superseded }
#[rustfmt::skip]
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub enum RecordKind { Req, Nfr, Adr }
#[rustfmt::skip]
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub enum Modal { Must, Should, MustNot }
impl Id {
    pub fn kind(&self) -> RecordKind {
        match &self.0[..3] {
            "REQ" => RecordKind::Req,
            "NFR" => RecordKind::Nfr,
            _ => RecordKind::Adr,
        }
    }
}
#[rustfmt::skip]
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub enum Level { Header, Item, Section, Label }
#[rustfmt::skip]
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub enum Shape { Text, Date, Version, Status, Id, IdList, TextList, StatementList, Checklist, LinkList, Group, Derived }
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct FieldMeta {
    pub name: &'static str,
    pub label: &'static str,
    pub level: Level,
    pub shape: Shape,
    pub section: Option<&'static str>,
    pub required: bool,
    pub sql_type: &'static str,
}
#[rustfmt::skip]
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct Identity { pub id: Id, pub title: String }
#[rustfmt::skip]
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct Lifecycle { pub status: Status, pub version: Version, pub created: Date, pub last_updated: Date, pub owner: String, #[serde(default)] pub supersedes: Option<Id>, #[serde(default)] pub superseded_by: Option<Id> }
#[rustfmt::skip]
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct Statement { pub modal: Modal, pub text: String }
#[rustfmt::skip]
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct CheckItem { pub text: String, pub checked: Option<bool> }
#[rustfmt::skip]
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct IdItem { pub id: Id, pub note: Option<String> }
#[rustfmt::skip]
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct LinkItem { pub text: String, pub href: String, pub note: Option<String> }
#[rustfmt::skip]
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct RelatedDocuments { pub text: String, pub requirements: Vec<IdItem>, pub architecture_decisions: Vec<IdItem>, pub design_documents: Vec<LinkItem>, pub work_items: Vec<LinkItem>, pub external_references: Vec<LinkItem> }
#[rustfmt::skip]
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct RequirementStatement { pub text: String, pub statements: Vec<Statement> }
#[rustfmt::skip]
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct SuccessCriteria { pub text: String, pub acceptance_criteria: Vec<CheckItem>, pub test_evidence: Vec<String> }
#[rustfmt::skip]
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct Dependencies { pub text: String, pub requires: Vec<IdItem>, pub related: Vec<IdItem> }
#[rustfmt::skip]
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct ProductApplicability { pub text: String, pub applies_to: Vec<String>, pub does_not_apply_to: Vec<String> }
#[rustfmt::skip]
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct ImplementationNotes { pub text: String, pub key_considerations: Vec<String> }
#[rustfmt::skip]
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct TestStrategy { pub text: String, pub test_types: Vec<String> }
#[rustfmt::skip]
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct Alternative { pub name: String, pub description: String, pub pros: Vec<String>, pub cons: Vec<String>, pub why_rejected: String }
#[rustfmt::skip]
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct Alternatives { pub text: String, pub groups: Vec<Alternative> }
#[rustfmt::skip]
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct Context { pub text: String, pub background: String, pub problem_statement: String }
#[rustfmt::skip]
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct DecisionSection { pub text: String, pub chosen_approach: String, pub key_principles: Vec<String> }
#[rustfmt::skip]
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct DecisionRationale { pub text: String, pub benefits: Vec<String>, pub trade_offs: Vec<String> }
#[rustfmt::skip]
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct Consequences { pub text: String, pub positive: Vec<String>, pub negative: Vec<String>, pub neutral: Vec<String> }
#[rustfmt::skip]
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct Implementation { pub text: String, pub key_components: Vec<String>, pub integration_points: Vec<String>, pub code_examples: String }
#[rustfmt::skip]
#[derive(Clone, Debug, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct ImpactAnalysis { pub text: String, pub affected_components: String, pub performance_impact: String, pub security_impact: String, pub maintainability_impact: String }
#[rustfmt::skip]
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct Requirement { #[serde(flatten)] pub identity: Identity, #[serde(flatten)] pub lifecycle: Lifecycle, #[serde(default)] pub requirement_statement: RequirementStatement, #[serde(default)] pub rationale: String, #[serde(default)] pub success_criteria: SuccessCriteria, #[serde(default)] pub dependencies: Dependencies, #[serde(default)] pub product_applicability: ProductApplicability, #[serde(default)] pub implementation_notes: ImplementationNotes, #[serde(default)] pub test_strategy: TestStrategy, #[serde(default)] pub related_documents: RelatedDocuments }
#[rustfmt::skip]
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct Decision { #[serde(flatten)] pub identity: Identity, #[serde(flatten)] pub lifecycle: Lifecycle, pub decision_date: Date, pub context: Context, pub decision: DecisionSection, pub rationale: DecisionRationale, pub consequences: Consequences, #[serde(default)] pub alternatives: Alternatives, #[serde(default)] pub implementation: Implementation, #[serde(default)] pub impact_analysis: ImpactAnalysis, #[serde(default)] pub related_documents: RelatedDocuments }
#[allow(dead_code)]
#[derive(JsonSchema)]
struct Records {
    requirements: Vec<Requirement>,
    decisions: Vec<Decision>,
}
pub trait HasIdentity {
    fn identity(&self) -> &Identity;
}
pub trait HasLifecycle {
    fn lifecycle(&self) -> &Lifecycle;
}
pub trait HasRelatedDocuments {
    fn related_documents(&self) -> &RelatedDocuments;
}
#[rustfmt::skip] impl HasIdentity for Requirement { fn identity(&self) -> &Identity { &self.identity } }
#[rustfmt::skip] impl HasIdentity for Decision { fn identity(&self) -> &Identity { &self.identity } }
#[rustfmt::skip] impl HasLifecycle for Requirement { fn lifecycle(&self) -> &Lifecycle { &self.lifecycle } }
#[rustfmt::skip] impl HasLifecycle for Decision { fn lifecycle(&self) -> &Lifecycle { &self.lifecycle } }
#[rustfmt::skip] impl HasRelatedDocuments for Requirement { fn related_documents(&self) -> &RelatedDocuments { &self.related_documents } }
#[rustfmt::skip] impl HasRelatedDocuments for Decision { fn related_documents(&self) -> &RelatedDocuments { &self.related_documents } }
#[rustfmt::skip]
const FIELDS: &[FieldMeta] = &[
    FieldMeta{name:"id",label:"ID",level:Level::Item,shape:Shape::Id,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"title",label:"Title",level:Level::Item,shape:Shape::Text,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"status",label:"Status",level:Level::Header,shape:Shape::Status,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"version",label:"Version",level:Level::Header,shape:Shape::Version,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"created",label:"Created",level:Level::Header,shape:Shape::Date,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"last_updated",label:"Last Updated",level:Level::Header,shape:Shape::Date,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"owner",label:"Owner",level:Level::Header,shape:Shape::Text,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"supersedes",label:"Supersedes",level:Level::Header,shape:Shape::Id,section:None,required:false,sql_type:"TEXT"}, FieldMeta{name:"superseded_by",label:"Superseded By",level:Level::Header,shape:Shape::Id,section:None,required:false,sql_type:"TEXT"}, FieldMeta{name:"id_range",label:"ID Range",level:Level::Header,shape:Shape::Derived,section:None,required:false,sql_type:"TEXT"}, FieldMeta{name:"decision_date",label:"Decision Date",level:Level::Header,shape:Shape::Date,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"status",label:"Status",level:Level::Item,shape:Shape::Status,section:None,required:true,sql_type:"TEXT"},
    FieldMeta{name:"requirement_statement",label:"Requirement Statement",level:Level::Section,shape:Shape::StatementList,section:Some("__requirements"),required:true,sql_type:"TEXT"}, FieldMeta{name:"rationale",label:"Rationale",level:Level::Section,shape:Shape::Text,section:Some("__requirements"),required:true,sql_type:"TEXT"}, FieldMeta{name:"success_criteria",label:"Success Criteria",level:Level::Section,shape:Shape::Checklist,section:Some("__requirements"),required:true,sql_type:"TEXT"}, FieldMeta{name:"dependencies",label:"Dependencies",level:Level::Section,shape:Shape::IdList,section:Some("__requirements"),required:false,sql_type:"TEXT"}, FieldMeta{name:"product_applicability",label:"Product Applicability",level:Level::Section,shape:Shape::TextList,section:Some("__requirements"),required:false,sql_type:"TEXT"}, FieldMeta{name:"implementation_notes",label:"Implementation Notes",level:Level::Section,shape:Shape::TextList,section:Some("__requirements"),required:false,sql_type:"TEXT"}, FieldMeta{name:"test_strategy",label:"Test Strategy",level:Level::Section,shape:Shape::TextList,section:Some("__requirements"),required:false,sql_type:"TEXT"}, FieldMeta{name:"related_documents",label:"Related Documents",level:Level::Section,shape:Shape::Group,section:None,required:false,sql_type:"TEXT"},
    FieldMeta{name:"statements",label:"MUST Statements",level:Level::Label,shape:Shape::StatementList,section:Some("Requirement Statement"),required:false,sql_type:"TEXT"}, FieldMeta{name:"statements",label:"SHOULD Statements",level:Level::Label,shape:Shape::StatementList,section:Some("Requirement Statement"),required:false,sql_type:"TEXT"}, FieldMeta{name:"statements",label:"MUST NOT Statements",level:Level::Label,shape:Shape::StatementList,section:Some("Requirement Statement"),required:false,sql_type:"TEXT"}, FieldMeta{name:"acceptance_criteria",label:"Acceptance Criteria",level:Level::Label,shape:Shape::Checklist,section:Some("Success Criteria"),required:false,sql_type:"TEXT"}, FieldMeta{name:"test_evidence",label:"Test Evidence",level:Level::Label,shape:Shape::TextList,section:Some("Success Criteria"),required:false,sql_type:"TEXT"}, FieldMeta{name:"requires",label:"Requires",level:Level::Label,shape:Shape::IdList,section:Some("Dependencies"),required:false,sql_type:"TEXT"}, FieldMeta{name:"related",label:"Related",level:Level::Label,shape:Shape::IdList,section:Some("Dependencies"),required:false,sql_type:"TEXT"}, FieldMeta{name:"applies_to",label:"Applies To",level:Level::Label,shape:Shape::TextList,section:Some("Product Applicability"),required:false,sql_type:"TEXT"}, FieldMeta{name:"does_not_apply_to",label:"Does Not Apply To",level:Level::Label,shape:Shape::TextList,section:Some("Product Applicability"),required:false,sql_type:"TEXT"}, FieldMeta{name:"key_considerations",label:"Key Considerations",level:Level::Label,shape:Shape::TextList,section:Some("Implementation Notes"),required:false,sql_type:"TEXT"}, FieldMeta{name:"test_types",label:"Test Types",level:Level::Label,shape:Shape::TextList,section:Some("Test Strategy"),required:false,sql_type:"TEXT"}, FieldMeta{name:"requirements",label:"Requirements",level:Level::Label,shape:Shape::IdList,section:Some("Related Documents"),required:false,sql_type:"TEXT"}, FieldMeta{name:"architecture_decisions",label:"Architecture Decisions",level:Level::Label,shape:Shape::IdList,section:Some("Related Documents"),required:false,sql_type:"TEXT"}, FieldMeta{name:"design_documents",label:"Design Documents",level:Level::Label,shape:Shape::LinkList,section:Some("Related Documents"),required:false,sql_type:"TEXT"}, FieldMeta{name:"work_items",label:"Work Items",level:Level::Label,shape:Shape::LinkList,section:Some("Related Documents"),required:false,sql_type:"TEXT"}, FieldMeta{name:"external_references",label:"External References",level:Level::Label,shape:Shape::LinkList,section:Some("Related Documents"),required:false,sql_type:"TEXT"},
    FieldMeta{name:"context",label:"Context",level:Level::Section,shape:Shape::Text,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"decision",label:"Decision",level:Level::Section,shape:Shape::Text,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"rationale",label:"Rationale",level:Level::Section,shape:Shape::Text,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"consequences",label:"Consequences",level:Level::Section,shape:Shape::Text,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"alternatives",label:"Alternatives Considered",level:Level::Section,shape:Shape::Group,section:None,required:false,sql_type:"TEXT"}, FieldMeta{name:"implementation",label:"Implementation",level:Level::Section,shape:Shape::Text,section:None,required:false,sql_type:"TEXT"}, FieldMeta{name:"impact_analysis",label:"Impact Analysis",level:Level::Section,shape:Shape::Text,section:None,required:false,sql_type:"TEXT"},
    FieldMeta{name:"background",label:"Background",level:Level::Label,shape:Shape::Text,section:Some("Context"),required:false,sql_type:"TEXT"}, FieldMeta{name:"problem_statement",label:"Problem Statement",level:Level::Label,shape:Shape::Text,section:Some("Context"),required:false,sql_type:"TEXT"}, FieldMeta{name:"chosen_approach",label:"Chosen Approach",level:Level::Label,shape:Shape::Text,section:Some("Decision"),required:false,sql_type:"TEXT"}, FieldMeta{name:"key_principles",label:"Key Principles",level:Level::Label,shape:Shape::TextList,section:Some("Decision"),required:false,sql_type:"TEXT"}, FieldMeta{name:"benefits",label:"Benefits",level:Level::Label,shape:Shape::TextList,section:Some("Rationale"),required:false,sql_type:"TEXT"}, FieldMeta{name:"trade_offs",label:"Trade-offs",level:Level::Label,shape:Shape::TextList,section:Some("Rationale"),required:false,sql_type:"TEXT"}, FieldMeta{name:"positive",label:"Positive",level:Level::Label,shape:Shape::TextList,section:Some("Consequences"),required:false,sql_type:"TEXT"}, FieldMeta{name:"negative",label:"Negative",level:Level::Label,shape:Shape::TextList,section:Some("Consequences"),required:false,sql_type:"TEXT"}, FieldMeta{name:"neutral",label:"Neutral",level:Level::Label,shape:Shape::TextList,section:Some("Consequences"),required:false,sql_type:"TEXT"}, FieldMeta{name:"description",label:"Description",level:Level::Label,shape:Shape::Text,section:Some("Alternatives Considered"),required:false,sql_type:"TEXT"}, FieldMeta{name:"pros",label:"Pros",level:Level::Label,shape:Shape::TextList,section:Some("Alternatives Considered"),required:false,sql_type:"TEXT"}, FieldMeta{name:"cons",label:"Cons",level:Level::Label,shape:Shape::TextList,section:Some("Alternatives Considered"),required:false,sql_type:"TEXT"}, FieldMeta{name:"why_rejected",label:"Why Rejected",level:Level::Label,shape:Shape::Text,section:Some("Alternatives Considered"),required:false,sql_type:"TEXT"}, FieldMeta{name:"key_components",label:"Key Components",level:Level::Label,shape:Shape::TextList,section:Some("Implementation"),required:false,sql_type:"TEXT"}, FieldMeta{name:"integration_points",label:"Integration Points",level:Level::Label,shape:Shape::TextList,section:Some("Implementation"),required:false,sql_type:"TEXT"}, FieldMeta{name:"code_examples",label:"Code Examples",level:Level::Label,shape:Shape::Text,section:Some("Implementation"),required:false,sql_type:"TEXT"}, FieldMeta{name:"affected_components",label:"Affected Components",level:Level::Label,shape:Shape::Text,section:Some("Impact Analysis"),required:false,sql_type:"TEXT"}, FieldMeta{name:"performance_impact",label:"Performance Impact",level:Level::Label,shape:Shape::Text,section:Some("Impact Analysis"),required:false,sql_type:"TEXT"}, FieldMeta{name:"security_impact",label:"Security Impact",level:Level::Label,shape:Shape::Text,section:Some("Impact Analysis"),required:false,sql_type:"TEXT"}, FieldMeta{name:"maintainability_impact",label:"Maintainability Impact",level:Level::Label,shape:Shape::Text,section:Some("Impact Analysis"),required:false,sql_type:"TEXT"},
];
pub trait Table {
    const NAME: &'static str;
    fn fields() -> Vec<FieldMeta>;
}
impl Table for Requirement {
    const NAME: &'static str = "requirements";
    fn fields() -> Vec<FieldMeta> {
        FIELDS.to_vec()
    }
}
impl Table for Decision {
    const NAME: &'static str = "decisions";
    fn fields() -> Vec<FieldMeta> {
        FIELDS.to_vec()
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
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
#[rustfmt::skip]
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct Diagnostic { pub file: String, pub line: u32, pub rule: Rule, pub id: Option<Id>, pub label: Option<String>, #[serde(skip_deserializing, default)] pub message: &'static str, pub allowed: Option<Vec<String>>, #[serde(skip_deserializing, default)] pub remedy: &'static str }
#[derive(Clone, Debug, Serialize)]
pub struct Bound {
    pub requirements: Vec<Requirement>,
    pub decisions: Vec<Decision>,
    pub diagnostics: Vec<Diagnostic>,
}
const MISSING: (&str, &str) = ("required field is missing", "Add the required field.");
const BAD: (&str, &str) = ("field value is invalid", "Use the documented value format.");
const UNKNOWN_SECTION: (&str, &str) = (
    "section is not defined",
    "Remove the section or use an allowed section.",
);
const UNKNOWN_LABEL: (&str, &str) = (
    "label is not defined",
    "Remove the label or use an allowed label.",
);
const DUPLICATE: (&str, &str) = ("duplicate identifier", "Make the identifier unique.");
const DANGLING_REFERENCE: (&str, &str) = (
    "reference does not declare a record",
    "Declare the referenced identifier or remove the reference.",
);
#[rustfmt::skip] fn details(rule: &Rule) -> (&'static str, &'static str) { match rule { Rule::MissingId | Rule::MissingField => MISSING, Rule::BadValue => BAD, Rule::UnknownSection => UNKNOWN_SECTION, Rule::UnknownLabel => UNKNOWN_LABEL, Rule::DuplicateId => DUPLICATE, Rule::DanglingReference => DANGLING_REFERENCE } }
fn diagnostic(
    file: &str,
    line: u32,
    rule: Rule,
    id: Option<Id>,
    label: Option<String>,
) -> Diagnostic {
    let (message, remedy) = details(&rule);
    Diagnostic {
        file: file.into(),
        line,
        rule,
        id,
        label,
        message,
        allowed: None,
        remedy,
    }
}
fn same(left: &str, right: &str) -> bool {
    left.eq_ignore_ascii_case(right)
}
fn named<'a>(tree: &'a serde_json::Value, key: &str) -> Option<&'a serde_json::Value> {
    tree.as_object()?
        .iter()
        .find(|(name, _)| same(name, key))
        .map(|(_, value)| value)
}
fn string(tree: &serde_json::Value, key: &str) -> Option<String> {
    let value = named(tree, key)?;
    value
        .as_str()
        .or_else(|| value.get("value").and_then(|v| v.as_str()))
        .map(str::to_owned)
}
fn tree_line(tree: &serde_json::Value) -> u32 {
    tree.get("line").and_then(|v| v.as_u64()).unwrap_or(0) as u32
}
fn table_fields(kind: RecordKind) -> Vec<FieldMeta> {
    FIELDS
        .iter()
        .filter(|f| match kind {
            RecordKind::Adr => {
                f.section.is_none()
                    && f.name != "requirement_statement"
                    && f.name != "success_criteria"
                    && f.name != "dependencies"
                    && f.name != "product_applicability"
                    && f.name != "implementation_notes"
                    && f.name != "test_strategy"
                    || matches!(
                        f.section,
                        Some(
                            "Related Documents"
                                | "Context"
                                | "Decision"
                                | "Rationale"
                                | "Consequences"
                                | "Alternatives Considered"
                                | "Implementation"
                                | "Impact Analysis"
                        )
                    )
                    || f.label == "Related Documents"
            }
            _ => {
                !(matches!(
                    f.label,
                    "Decision Date"
                        | "Context"
                        | "Decision"
                        | "Consequences"
                        | "Alternatives Considered"
                        | "Implementation"
                        | "Impact Analysis"
                ) || f.name == "rationale" && f.section.is_none()
                    || matches!(
                        f.section,
                        Some(
                            "Context"
                                | "Decision"
                                | "Rationale"
                                | "Consequences"
                                | "Alternatives Considered"
                                | "Implementation"
                                | "Impact Analysis"
                        )
                    ))
            }
        })
        .cloned()
        .collect()
}
fn allowed(fields: &[FieldMeta], level: Level, section: Option<&str>) -> Vec<String> {
    fields
        .iter()
        .filter(|f| f.level == level && (level != Level::Label || f.section == section))
        .fold(Vec::new(), |mut labels, f| {
            if !labels.iter().any(|label| label == f.label) {
                labels.push(f.label.into());
            }
            labels
        })
}
fn unknown(
    file: &str,
    line: u32,
    rule: Rule,
    id: Option<Id>,
    label: String,
    allowed: Vec<String>,
) -> Diagnostic {
    let mut out = diagnostic(file, line, rule, id, Some(label));
    out.allowed = Some(allowed);
    out
}
fn text(value: &serde_json::Value, key: &str) -> Vec<String> {
    value
        .get(key)
        .and_then(|x| x.as_array())
        .into_iter()
        .flatten()
        .filter_map(|x| x.get("text").and_then(|x| x.as_str()).map(str::to_owned))
        .collect()
}
fn prose(value: &serde_json::Value) -> String {
    text(value, "prose").join("\n")
}
fn label<'a>(section: &'a serde_json::Value, name: &str) -> Option<&'a serde_json::Value> {
    section.get("labels")?.as_array()?.iter().find(|x| {
        x.get("name")
            .and_then(|x| x.as_str())
            .is_some_and(|value| same(value, name))
    })
}
fn id_items(
    value: Option<&serde_json::Value>,
    file: &str,
    id: &Id,
    name: &str,
    out: &mut Vec<Diagnostic>,
) -> Vec<IdItem> {
    text(value.unwrap_or(&serde_json::Value::Null), "items")
        .into_iter()
        .filter_map(|raw| {
            let (token, tail) = if let Some(rest) = raw.strip_prefix('[') {
                let (token, rest) = rest.split_once("](")?;
                let (_, tail) = rest.split_once(')')?;
                (
                    token,
                    tail.trim_matches(|c: char| c == ' ' || c == '-' || c == '—' || c == ':'),
                )
            } else {
                raw.split_once(' ').map_or((raw.as_str(), ""), |x| x)
            };
            let tail = tail.trim_matches(|c: char| c == ' ' || c == '-' || c == '—' || c == ':');
            match token.parse() {
                Ok(target) => Some(IdItem {
                    id: target,
                    note: (!tail.is_empty()).then(|| tail.into()),
                }),
                Err(_) => {
                    out.push(diagnostic(
                        file,
                        value
                            .and_then(|v| v.get("line"))
                            .and_then(|v| v.as_u64())
                            .unwrap_or(0) as u32,
                        Rule::BadValue,
                        Some(id.clone()),
                        Some(name.into()),
                    ));
                    None
                }
            }
        })
        .collect()
}
fn links(value: Option<&serde_json::Value>) -> Vec<LinkItem> {
    text(value.unwrap_or(&serde_json::Value::Null), "items")
        .into_iter()
        .filter_map(|raw| {
            let rest = raw.strip_prefix('[')?;
            let (text, rest) = rest.split_once("](")?;
            let (href, note) = rest.split_once(')')?;
            Some(LinkItem {
                text: text.into(),
                href: href.into(),
                note: (!note.trim().is_empty()).then(|| {
                    note.trim_matches(|c: char| c == ' ' || c == '-' || c == '—' || c == ':')
                        .into()
                }),
            })
        })
        .collect()
}
fn checklist(value: Option<&serde_json::Value>) -> Vec<CheckItem> {
    text(value.unwrap_or(&serde_json::Value::Null), "items")
        .into_iter()
        .map(|raw| {
            let (checked, text) = if let Some(x) = raw
                .strip_prefix("[x] ")
                .or_else(|| raw.strip_prefix("[X] "))
            {
                (Some(true), x)
            } else if let Some(x) = raw.strip_prefix("[ ] ") {
                (Some(false), x)
            } else {
                (None, raw.as_str())
            };
            CheckItem {
                text: text.into(),
                checked,
            }
        })
        .collect()
}
fn section<'a>(item: &'a serde_json::Value, name: &str) -> Option<&'a serde_json::Value> {
    item.get("sections")?.as_array()?.iter().find(|x| {
        x.get("name")
            .and_then(|x| x.as_str())
            .is_some_and(|value| same(value, name))
    })
}
pub fn bind_file(tree: &serde_json::Value) -> Bound {
    let file = tree
        .get("path")
        .and_then(|v| v.as_str())
        .unwrap_or_default();
    let header = tree.get("header").unwrap_or(&serde_json::Value::Null);
    let mut out = Bound {
        requirements: vec![],
        decisions: vec![],
        diagnostics: vec![],
    };
    let records = tree.get("records").and_then(|v| v.as_array());
    if records.is_none_or(Vec::is_empty) {
        out.diagnostics
            .push(diagnostic(file, 0, Rule::MissingId, None, None));
    }
    for (name, value) in header.as_object().into_iter().flatten() {
        if !FIELDS
            .iter()
            .any(|f| f.level == Level::Header && same(f.label, name))
        {
            out.diagnostics.push(unknown(
                file,
                tree_line(value),
                Rule::UnknownLabel,
                None,
                name.clone(),
                allowed(FIELDS, Level::Header, None),
            ));
        }
    }
    for item in records.into_iter().flatten() {
        let line = tree_line(item);
        let raw_id = string(item, "id");
        let id = raw_id.as_deref().map(str::parse::<Id>).transpose();
        let title = string(item, "title");
        let fields = item.get("fields").unwrap_or(&serde_json::Value::Null);
        let val = |key: &str| string(fields, key).or_else(|| string(header, key));
        let (status, version, created, last_updated, owner) = (
            val(FIELDS[2].label),
            val(FIELDS[3].label),
            val(FIELDS[4].label),
            val(FIELDS[5].label),
            val(FIELDS[6].label),
        );
        let (supersedes, superseded_by, decision_date) = (
            val("Supersedes"),
            val("Superseded By"),
            val("Decision Date"),
        );
        if raw_id.is_none() {
            out.diagnostics
                .push(diagnostic(file, line, Rule::MissingId, None, None));
            continue;
        }
        let id = match id {
            Ok(Some(id)) => id,
            _ => {
                out.diagnostics.push(diagnostic(
                    file,
                    line,
                    Rule::BadValue,
                    None,
                    Some("id".into()),
                ));
                continue;
            }
        };
        let fields_for = table_fields(id.kind());
        for (name, value) in fields.as_object().into_iter().flatten() {
            if !same(name, "Status") {
                out.diagnostics.push(unknown(
                    file,
                    tree_line(value),
                    Rule::UnknownLabel,
                    Some(id.clone()),
                    name.clone(),
                    allowed(&fields_for, Level::Item, None),
                ));
            }
        }
        for section in item
            .get("sections")
            .and_then(|v| v.as_array())
            .into_iter()
            .flatten()
        {
            let name = section
                .get("name")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_owned();
            let known = fields_for
                .iter()
                .any(|f| f.level == Level::Section && same(f.label, &name));
            if !known {
                out.diagnostics.push(unknown(
                    file,
                    tree_line(section),
                    Rule::UnknownSection,
                    Some(id.clone()),
                    name.clone(),
                    allowed(&fields_for, Level::Section, None),
                ));
            }
            for label in section
                .get("labels")
                .and_then(|v| v.as_array())
                .into_iter()
                .flatten()
            {
                let name = label
                    .get("name")
                    .and_then(|v| v.as_str())
                    .unwrap_or_default()
                    .to_owned();
                if known
                    && !fields_for.iter().any(|f| {
                        f.level == Level::Label
                            && f.section.is_some_and(|value| {
                                same(
                                    value,
                                    section
                                        .get("name")
                                        .and_then(|x| x.as_str())
                                        .unwrap_or_default(),
                                )
                            })
                            && same(f.label, &name)
                    })
                {
                    out.diagnostics.push(unknown(
                        file,
                        tree_line(label),
                        Rule::UnknownLabel,
                        Some(id.clone()),
                        name,
                        allowed(
                            &fields_for,
                            Level::Label,
                            section.get("name").and_then(|x| x.as_str()),
                        ),
                    ));
                }
            }
            for group in section
                .get("groups")
                .and_then(|v| v.as_array())
                .into_iter()
                .flatten()
            {
                let group_allowed = fields_for.iter().any(|f| {
                    f.level == Level::Section && same(f.label, &name) && f.shape == Shape::Group
                });
                if !group_allowed {
                    out.diagnostics.push(unknown(
                        file,
                        tree_line(group),
                        Rule::UnknownSection,
                        Some(id.clone()),
                        group
                            .get("name")
                            .and_then(|v| v.as_str())
                            .unwrap_or_default()
                            .into(),
                        vec![],
                    ));
                }
                for label in group
                    .get("labels")
                    .and_then(|v| v.as_array())
                    .into_iter()
                    .flatten()
                {
                    let label_name = label
                        .get("name")
                        .and_then(|v| v.as_str())
                        .unwrap_or_default();
                    if group_allowed
                        && !fields_for.iter().any(|f| {
                            f.level == Level::Label
                                && f.section.is_some_and(|value| same(value, name.as_str()))
                                && same(f.label, label_name)
                        })
                    {
                        out.diagnostics.push(unknown(
                            file,
                            tree_line(label),
                            Rule::UnknownLabel,
                            Some(id.clone()),
                            label_name.into(),
                            allowed(&fields_for, Level::Label, Some(name.as_str())),
                        ));
                    }
                }
            }
        }
        if title.is_none()
            || status.is_none()
            || version.is_none()
            || created.is_none()
            || last_updated.is_none()
            || owner.is_none()
            || (id.kind() == RecordKind::Adr && decision_date.is_none())
        {
            out.diagnostics
                .push(diagnostic(file, line, Rule::MissingField, Some(id), None));
            continue;
        }
        let parsed = (
            serde_json::from_str(&format!("\"{}\"", status.unwrap())).ok(),
            version.unwrap().parse(),
            created.unwrap().parse(),
            last_updated.unwrap().parse(),
        );
        if let (Some(status), Ok(version), Ok(created), Ok(last_updated)) = parsed {
            let parse_link = |raw: Option<String>| raw.map(|value| value.parse::<Id>()).transpose();
            let (supersedes, superseded_by) =
                match (parse_link(supersedes), parse_link(superseded_by)) {
                    (Ok(supersedes), Ok(superseded_by)) => (supersedes, superseded_by),
                    _ => {
                        out.diagnostics.push(diagnostic(
                            file,
                            line,
                            Rule::BadValue,
                            Some(id.clone()),
                            None,
                        ));
                        continue;
                    }
                };
            if supersedes
                .as_ref()
                .is_some_and(|target| target.kind() != id.kind())
                || superseded_by
                    .as_ref()
                    .is_some_and(|target| target.kind() != id.kind())
            {
                out.diagnostics.push(diagnostic(
                    file,
                    line,
                    Rule::BadValue,
                    Some(id.clone()),
                    None,
                ));
                continue;
            }
            let decision_date = match decision_date.map(|value| value.parse::<Date>()).transpose() {
                Ok(value) => value,
                Err(_) => {
                    out.diagnostics.push(diagnostic(
                        file,
                        line,
                        Rule::BadValue,
                        Some(id.clone()),
                        Some("Decision Date".into()),
                    ));
                    continue;
                }
            };
            let row = Lifecycle {
                status,
                version,
                created,
                last_updated,
                owner: owner.unwrap(),
                supersedes,
                superseded_by,
            };
            let identity = Identity {
                id: id.clone(),
                title: title.unwrap(),
            };
            let related = section(item, "Related Documents");
            let related_documents = RelatedDocuments {
                text: related.map(prose).unwrap_or_default(),
                requirements: id_items(
                    related.and_then(|x| label(x, "Requirements")),
                    file,
                    &id,
                    "Requirements",
                    &mut out.diagnostics,
                ),
                architecture_decisions: id_items(
                    related.and_then(|x| label(x, "Architecture Decisions")),
                    file,
                    &id,
                    "Architecture Decisions",
                    &mut out.diagnostics,
                ),
                design_documents: links(related.and_then(|x| label(x, "Design Documents"))),
                work_items: links(related.and_then(|x| label(x, "Work Items"))),
                external_references: links(related.and_then(|x| label(x, "External References"))),
            };
            if identity.id.kind() == RecordKind::Adr {
                let (context, decision, rationale, consequences) = (
                    section(item, "Context"),
                    section(item, "Decision"),
                    section(item, "Rationale"),
                    section(item, "Consequences"),
                );
                if [context, decision, rationale, consequences]
                    .iter()
                    .any(Option::is_none)
                {
                    out.diagnostics.push(diagnostic(
                        file,
                        line,
                        Rule::MissingField,
                        Some(id.clone()),
                        None,
                    ));
                    continue;
                }
                let alternatives = section(item, "Alternatives Considered");
                let groups = alternatives
                    .and_then(|s| s.get("groups"))
                    .and_then(|v| v.as_array())
                    .into_iter()
                    .flatten()
                    .map(|group| Alternative {
                        name: group
                            .get("name")
                            .and_then(|v| v.as_str())
                            .and_then(|n| n.split_once(": ").map(|(_, n)| n))
                            .unwrap_or_default()
                            .into(),
                        description: label(group, "Description").map(prose).unwrap_or_default(),
                        pros: text(
                            label(group, "Pros").unwrap_or(&serde_json::Value::Null),
                            "items",
                        ),
                        cons: text(
                            label(group, "Cons").unwrap_or(&serde_json::Value::Null),
                            "items",
                        ),
                        why_rejected: label(group, "Why Rejected").map(prose).unwrap_or_default(),
                    })
                    .collect();
                out.decisions.push(Decision {
                    identity,
                    lifecycle: row,
                    decision_date: decision_date.unwrap(),
                    context: Context {
                        text: context.map(prose).unwrap_or_default(),
                        background: context
                            .and_then(|s| label(s, "Background"))
                            .map(prose)
                            .unwrap_or_default(),
                        problem_statement: context
                            .and_then(|s| label(s, "Problem Statement"))
                            .map(prose)
                            .unwrap_or_default(),
                    },
                    decision: DecisionSection {
                        text: decision.map(prose).unwrap_or_default(),
                        chosen_approach: decision
                            .and_then(|s| label(s, "Chosen Approach"))
                            .map(prose)
                            .unwrap_or_default(),
                        key_principles: text(
                            decision
                                .and_then(|s| label(s, "Key Principles"))
                                .unwrap_or(&serde_json::Value::Null),
                            "items",
                        ),
                    },
                    rationale: DecisionRationale {
                        text: rationale.map(prose).unwrap_or_default(),
                        benefits: text(
                            rationale
                                .and_then(|s| label(s, "Benefits"))
                                .unwrap_or(&serde_json::Value::Null),
                            "items",
                        ),
                        trade_offs: text(
                            rationale
                                .and_then(|s| label(s, "Trade-offs"))
                                .unwrap_or(&serde_json::Value::Null),
                            "items",
                        ),
                    },
                    consequences: Consequences {
                        text: consequences.map(prose).unwrap_or_default(),
                        positive: text(
                            consequences
                                .and_then(|s| label(s, "Positive"))
                                .unwrap_or(&serde_json::Value::Null),
                            "items",
                        ),
                        negative: text(
                            consequences
                                .and_then(|s| label(s, "Negative"))
                                .unwrap_or(&serde_json::Value::Null),
                            "items",
                        ),
                        neutral: text(
                            consequences
                                .and_then(|s| label(s, "Neutral"))
                                .unwrap_or(&serde_json::Value::Null),
                            "items",
                        ),
                    },
                    alternatives: Alternatives {
                        text: alternatives.map(prose).unwrap_or_default(),
                        groups,
                    },
                    implementation: {
                        let s = section(item, "Implementation");
                        Implementation {
                            text: s.map(prose).unwrap_or_default(),
                            key_components: text(
                                s.and_then(|x| label(x, "Key Components"))
                                    .unwrap_or(&serde_json::Value::Null),
                                "items",
                            ),
                            integration_points: text(
                                s.and_then(|x| label(x, "Integration Points"))
                                    .unwrap_or(&serde_json::Value::Null),
                                "items",
                            ),
                            code_examples: s
                                .and_then(|x| label(x, "Code Examples"))
                                .map(prose)
                                .unwrap_or_default(),
                        }
                    },
                    impact_analysis: {
                        let s = section(item, "Impact Analysis");
                        ImpactAnalysis {
                            text: s.map(prose).unwrap_or_default(),
                            affected_components: s
                                .and_then(|x| label(x, "Affected Components"))
                                .map(prose)
                                .unwrap_or_default(),
                            performance_impact: s
                                .and_then(|x| label(x, "Performance Impact"))
                                .map(prose)
                                .unwrap_or_default(),
                            security_impact: s
                                .and_then(|x| label(x, "Security Impact"))
                                .map(prose)
                                .unwrap_or_default(),
                            maintainability_impact: s
                                .and_then(|x| label(x, "Maintainability Impact"))
                                .map(prose)
                                .unwrap_or_default(),
                        }
                    },
                    related_documents,
                })
            } else {
                let statement = section(item, "Requirement Statement");
                let success = section(item, "Success Criteria");
                if [statement, section(item, "Rationale"), success]
                    .iter()
                    .any(Option::is_none)
                {
                    out.diagnostics.push(diagnostic(
                        file,
                        line,
                        Rule::MissingField,
                        Some(id.clone()),
                        None,
                    ));
                }
                let deps = section(item, "Dependencies");
                let applicability = section(item, "Product Applicability");
                let notes = section(item, "Implementation Notes");
                let strategy = section(item, "Test Strategy");
                let mut statements = vec![];
                for (name, modal) in [
                    ("MUST Statements", Modal::Must),
                    ("SHOULD Statements", Modal::Should),
                    ("MUST NOT Statements", Modal::MustNot),
                ] {
                    statements.extend(
                        text(
                            statement
                                .and_then(|x| label(x, name))
                                .unwrap_or(&serde_json::Value::Null),
                            "items",
                        )
                        .into_iter()
                        .map(|text| Statement {
                            modal: modal.clone(),
                            text,
                        }),
                    );
                }
                out.requirements.push(Requirement {
                    identity,
                    lifecycle: row,
                    requirement_statement: RequirementStatement {
                        text: statement.map(prose).unwrap_or_default(),
                        statements,
                    },
                    rationale: section(item, "Rationale").map(prose).unwrap_or_default(),
                    success_criteria: SuccessCriteria {
                        text: success.map(prose).unwrap_or_default(),
                        acceptance_criteria: checklist(
                            success.and_then(|x| label(x, "Acceptance Criteria")),
                        ),
                        test_evidence: text(
                            success
                                .and_then(|x| label(x, "Test Evidence"))
                                .unwrap_or(&serde_json::Value::Null),
                            "items",
                        ),
                    },
                    dependencies: Dependencies {
                        text: deps.map(prose).unwrap_or_default(),
                        requires: id_items(
                            deps.and_then(|x| label(x, "Requires")),
                            file,
                            &id,
                            "Requires",
                            &mut out.diagnostics,
                        ),
                        related: id_items(
                            deps.and_then(|x| label(x, "Related")),
                            file,
                            &id,
                            "Related",
                            &mut out.diagnostics,
                        ),
                    },
                    product_applicability: ProductApplicability {
                        text: applicability.map(prose).unwrap_or_default(),
                        applies_to: text(
                            applicability
                                .and_then(|x| label(x, "Applies To"))
                                .unwrap_or(&serde_json::Value::Null),
                            "items",
                        ),
                        does_not_apply_to: text(
                            applicability
                                .and_then(|x| label(x, "Does Not Apply To"))
                                .unwrap_or(&serde_json::Value::Null),
                            "items",
                        ),
                    },
                    implementation_notes: ImplementationNotes {
                        text: notes.map(prose).unwrap_or_default(),
                        key_considerations: text(
                            notes
                                .and_then(|x| label(x, "Key Considerations"))
                                .unwrap_or(&serde_json::Value::Null),
                            "items",
                        ),
                    },
                    test_strategy: TestStrategy {
                        text: strategy.map(prose).unwrap_or_default(),
                        test_types: text(
                            strategy
                                .and_then(|x| label(x, "Test Types"))
                                .unwrap_or(&serde_json::Value::Null),
                            "items",
                        ),
                    },
                    related_documents,
                })
            }
        } else {
            out.diagnostics
                .push(diagnostic(file, line, Rule::BadValue, Some(id), None));
        }
    }
    out
}
pub fn check_inventory(requirements: &[Requirement], decisions: &[Decision]) -> Vec<Diagnostic> {
    let mut seen: HashMap<String, usize> = HashMap::new();
    for id in requirements
        .iter()
        .map(|x| &x.identity.id)
        .chain(decisions.iter().map(|x| &x.identity.id))
    {
        *seen.entry(id.0.clone()).or_default() += 1
    }
    let mut diagnostics: Vec<_> = requirements
        .iter()
        .map(|x| &x.identity.id)
        .chain(decisions.iter().map(|x| &x.identity.id))
        .filter(|x| seen[&x.0] > 1)
        .map(|id| diagnostic("", 0, Rule::DuplicateId, Some(id.clone()), None))
        .collect();
    let declared: HashSet<_> = seen.keys().cloned().collect();
    let mut check = |source: &Id, label: &str, values: &[IdItem]| {
        for item in values {
            if !declared.contains(&item.id.0) {
                diagnostics.push(diagnostic(
                    "",
                    0,
                    Rule::DanglingReference,
                    Some(source.clone()),
                    Some(label.into()),
                ));
            }
        }
    };
    for row in requirements {
        check(
            &row.identity.id,
            "Requirements",
            &row.related_documents.requirements,
        );
        check(
            &row.identity.id,
            "Architecture Decisions",
            &row.related_documents.architecture_decisions,
        );
        check(&row.identity.id, "Requires", &row.dependencies.requires);
        check(&row.identity.id, "Related", &row.dependencies.related);
    }
    for row in decisions {
        check(
            &row.identity.id,
            "Requirements",
            &row.related_documents.requirements,
        );
        check(
            &row.identity.id,
            "Architecture Decisions",
            &row.related_documents.architecture_decisions,
        );
    }
    diagnostics
}
pub fn field_table(table: &str) -> Vec<FieldMeta> {
    match table {
        "requirements" => table_fields(RecordKind::Req),
        "decisions" => table_fields(RecordKind::Adr),
        _ => vec![],
    }
}
pub fn sql_ddl() -> String {
    let columns = |table| {
        let mut names = HashSet::new();
        field_table(table)
            .iter()
            .filter(|f| f.name != "id_range" && f.level != Level::Label && names.insert(f.name))
            .map(|f| {
                if matches!(f.name, "supersedes" | "superseded_by") {
                    format!(
                        "{} TEXT REFERENCES {table}(id) DEFERRABLE INITIALLY DEFERRED",
                        f.name
                    )
                } else {
                    format!(
                        "{} {}{}",
                        f.name,
                        f.sql_type,
                        if f.required { " NOT NULL" } else { "" }
                    )
                }
            })
            .collect::<Vec<_>>()
            .join(", ")
    };
    let mut edges = Vec::new();
    for table in [Requirement::NAME, Decision::NAME] {
        let fields = field_table(table);
        for field in fields
            .iter()
            .filter(|f| f.level == Level::Label && f.shape == Shape::IdList)
        {
            let column = fields
                .iter()
                .find(|f| f.level == Level::Section && Some(f.label) == field.section)
                .expect("id-list fields have a section")
                .name;
            let label = field.name;
            edges.push(format!("SELECT {table}.id AS source, '{column}.{label}' AS path, json_extract(value, '$.id') AS target, key AS position FROM {table}, json_each({table}.{column}, '$.{label}')"));
        }
    }
    let edges = edges.join(" UNION ALL ");
    let status = "'Draft','Proposed','Active','Approved','Deprecated','Superseded'";
    format!(
        "CREATE TABLE requirements ({}, PRIMARY KEY (id), CHECK (status IN ({status})), CHECK (id GLOB 'REQ-*' OR id GLOB 'NFR-*'));\nCREATE TABLE decisions ({}, PRIMARY KEY (id), CHECK (status IN ({status})), CHECK (id GLOB 'ADR-*'));\nCREATE VIEW edges (source, path, target, position) AS {edges};\n",
        columns("requirements"),
        columns("decisions")
    )
}
pub fn json_schema() -> serde_json::Value {
    let mut schema = serde_json::to_value(schemars::schema_for!(Records)).unwrap();
    schema["x-raptor-fields"] = serde_json::to_value(FIELDS).unwrap();
    schema
}
#[rustfmt::skip]
pub fn summarize(diagnostics: &[Diagnostic]) -> serde_json::Value {
    let mut counts = BTreeMap::<String, usize>::new(); let mut groups = BTreeMap::<(String, Option<String>, Option<Vec<String>>, String), BTreeMap<String, Vec<u32>>>::new();
    for d in diagnostics { let rule = serde_json::to_value(&d.rule).unwrap().as_str().unwrap().to_owned(); *counts.entry(rule.clone()).or_default() += 1; groups.entry((rule, d.label.clone(), d.allowed.clone(), details(&d.rule).1.into())).or_default().entry(d.file.clone()).or_default().push(d.line); }
    serde_json::json!({"counts":counts,"groups":groups.into_iter().map(|((rule,label,allowed,remedy),files)| serde_json::json!({"rule":rule,"section":null,"label":label,"allowed":allowed,"count":files.values().map(Vec::len).sum::<usize>(),"files":files,"remedy":remedy})).collect::<Vec<_>>()})
}
#[cfg(feature = "python")]
#[pyo3::pymodule]
fn raptor_schema(m: &pyo3::Bound<'_, pyo3::types::PyModule>) -> pyo3::PyResult<()> {
    use pyo3::prelude::*;
    fn parse<T: serde::de::DeserializeOwned>(s: &str) -> PyResult<T> {
        serde_json::from_str(s).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }
    fn text<T: Serialize>(v: &T) -> PyResult<String> {
        serde_json::to_string(v).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
    }
    #[pyfn(m)]
    fn sql_ddl() -> String {
        crate::sql_ddl()
    }
    #[pyfn(m)]
    fn json_schema() -> PyResult<String> {
        text(&crate::json_schema())
    }
    #[pyfn(m)]
    fn field_table(table: String) -> PyResult<String> {
        text(&crate::field_table(&table))
    }
    #[pyfn(m)]
    fn bind_file(tree: String) -> PyResult<String> {
        text(&crate::bind_file(&parse(&tree)?))
    }
    #[pyfn(m)]
    fn check_inventory(requirements: String, decisions: String) -> PyResult<String> {
        let requirements: Vec<Requirement> = parse(&requirements)?;
        let decisions: Vec<Decision> = parse(&decisions)?;
        text(&crate::check_inventory(&requirements, &decisions))
    }
    #[pyfn(m)]
    fn summarize(diagnostics: String) -> PyResult<String> {
        text(&crate::summarize(&parse::<Vec<Diagnostic>>(&diagnostics)?))
    }
    Ok(())
}
