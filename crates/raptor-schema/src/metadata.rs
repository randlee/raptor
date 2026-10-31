use crate::schema::Modal;

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
    ("id", "ID", Both, Item, Shape::Id, Required),
    ("title", "Title", Both, Item, Text, Required),
    ("status", "Status", Both, Header, Shape::Status, Required),
    ("version", "Version", Both, Header, Shape::Version, Required),
    ("created", "Created", Both, Header, Shape::Date, Required),
    ("last_updated", "Last Updated", Both, Header, Shape::Date, Required),
    ("owner", "Owner", Both, Header, Text, Required),
    ("supersedes", "Supersedes", Both, Header, Shape::Id, Nullable),
    ("superseded_by", "Superseded By", Both, Header, Shape::Id, Nullable),
    ("id_range", "ID Range", Both, Header, Derived, Optional),
    ("decision_date", "Decision Date", Dec, Header, Shape::Date, Required),
    ("status", "Status", Both, Item, Shape::Status, Required),
    ("requirement_statement", "Requirement Statement", Req, SectionLevel, StatementList, Required),
    ("rationale", "Rationale", Req, SectionLevel, Text, Required),
    ("success_criteria", "Success Criteria", Req, SectionLevel, Checklist, Required),
    ("dependencies", "Dependencies", Req, SectionLevel, IdList, Optional),
    ("product_applicability", "Product Applicability", Req, SectionLevel, TextList, Optional),
    ("implementation_notes", "Implementation Notes", Req, SectionLevel, TextList, Optional),
    ("test_strategy", "Test Strategy", Req, SectionLevel, TextList, Optional),
    ("related_documents", "Related Documents", Both, SectionLevel, Group, Optional),
    ("statements", "MUST statements", Req, Label(S::Statement), Statements(Must), Optional),
    ("statements", "SHOULD statements", Req, Label(S::Statement), Statements(Should), Optional),
    ("statements", "MUST NOT statements", Req, Label(S::Statement), Statements(MustNot), Optional),
    ("acceptance_criteria", "Acceptance Criteria", Req, Label(S::Success), Checklist, Optional),
    ("test_evidence", "Test Evidence", Req, Label(S::Success), TextList, Optional),
    ("requires", "Requires", Req, Label(S::Dependencies), IdList, Optional),
    ("related", "Related", Req, Label(S::Dependencies), IdList, Optional),
    ("applies_to", "Applies To", Req, Label(S::Product), TextList, Optional),
    ("does_not_apply_to", "Does Not Apply To", Req, Label(S::Product), TextList, Optional),
    ("key_considerations", "Key Considerations", Req, Label(S::ImplNotes), TextList, Optional),
    ("test_types", "Test Types", Req, Label(S::Test), TextList, Optional),
    ("requirements", "Requirements", Both, Label(S::Related), IdList, Optional),
    ("architecture_decisions", "Architecture Decisions", Both, Label(S::Related), IdList, Optional),
    ("design_documents", "Design Documents", Both, Label(S::Related), LinkList, Optional),
    ("work_items", "Work Items", Both, Label(S::Related), LinkList, Optional),
    ("external_references", "External References", Both, Label(S::Related), LinkList, Optional),
    ("context", "Context", Dec, SectionLevel, Text, Required),
    ("decision", "Decision", Dec, SectionLevel, Text, Required),
    ("rationale", "Rationale", Dec, SectionLevel, Text, Required),
    ("consequences", "Consequences", Dec, SectionLevel, Text, Required),
    ("alternatives", "Alternatives Considered", Dec, SectionLevel, Group, Optional),
    ("implementation", "Implementation", Dec, SectionLevel, Text, Optional),
    ("impact_analysis", "Impact Analysis", Dec, SectionLevel, Text, Optional),
    ("background", "Background", Dec, Label(S::Context), Text, Optional),
    ("problem_statement", "Problem Statement", Dec, Label(S::Context), Text, Optional),
    ("chosen_approach", "Chosen Approach", Dec, Label(S::Decision), Text, Optional),
    ("key_principles", "Key Principles", Dec, Label(S::Decision), TextList, Optional),
    ("benefits", "Benefits", Both, Label(S::Rationale), TextList, Optional),
    ("trade_offs", "Trade-offs", Both, Label(S::Rationale), TextList, Optional),
    ("positive", "Positive", Dec, Label(S::Consequences), TextList, Optional),
    ("negative", "Negative", Dec, Label(S::Consequences), TextList, Optional),
    ("neutral", "Neutral", Dec, Label(S::Consequences), TextList, Optional),
    ("description", "Description", Dec, Label(S::Alternatives), Text, Optional),
    ("pros", "Pros", Dec, Label(S::Alternatives), TextList, Optional),
    ("cons", "Cons", Dec, Label(S::Alternatives), TextList, Optional),
    ("why_rejected", "Why Rejected", Dec, Label(S::Alternatives), Text, Optional),
    ("key_components", "Key Components", Dec, Label(S::Implementation), TextList, Optional),
    ("integration_points", "Integration Points", Dec, Label(S::Implementation), TextList, Optional),
    ("code_examples", "Code Examples", Dec, Label(S::Implementation), Text, Optional),
    ("affected_components", "Affected Components", Dec, Label(S::Impact), Text, Optional),
    ("performance_impact", "Performance Impact", Dec, Label(S::Impact), Text, Optional),
    ("security_impact", "Security Impact", Dec, Label(S::Impact), Text, Optional),
    ("maintainability_impact", "Maintainability Impact", Dec, Label(S::Impact), Text, Optional),
];
