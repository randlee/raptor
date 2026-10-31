use crate::{error::ErrorTable, schema::Modal};
use serde::Serialize;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
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
    Supersession,
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
#[derive(Clone, Copy)]
pub struct Field {
    pub name: &'static str,
    pub label: &'static str,
    pub table: Table,
    pub level: Level,
    pub shape: Shape,
    pub presence: Presence,
}
impl From<ErrorTable> for Table {
    fn from(table: ErrorTable) -> Self {
        match table {
            ErrorTable::Req => Self::Req,
            ErrorTable::Dec => Self::Dec,
        }
    }
}
