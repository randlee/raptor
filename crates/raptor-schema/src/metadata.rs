use crate::{
    error::TableId,
    schema::{Decision, Id, IdItem, Modal, Requirement},
};
use serde::Serialize;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FieldScope {
    All,
    Only(TableId),
}
impl Serialize for FieldScope {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.serialize_str(match self {
            Self::All => "Both",
            Self::Only(TableId::Req) => "Req",
            Self::Only(TableId::Dec) => "Dec",
        })
    }
}
#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum Presence {
    Required,
    Optional,
    Nullable,
}
#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum Level {
    Header,
    Item,
    Section,
    Label(Section),
}
#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum Shape {
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
impl Shape {
    /// Scalars are text; composite values are encoded as JSON text in SQLite.
    pub fn sql_type(self) -> &'static str {
        match self {
            Self::Text
            | Self::Date
            | Self::Version
            | Self::Status
            | Self::Id
            | Self::Supersession
            | Self::IdList
            | Self::TextList
            | Self::StatementList
            | Self::Statements(_)
            | Self::Checklist
            | Self::LinkList
            | Self::Group
            | Self::Derived => "TEXT",
        }
    }
}
#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) enum Section {
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
pub(crate) enum ReferenceAccess {
    List {
        requirement: for<'a> fn(&'a Requirement) -> &'a [IdItem],
        decision: Option<for<'a> fn(&'a Decision) -> &'a [IdItem]>,
    },
    Scalar {
        requirement: for<'a> fn(&'a Requirement) -> Option<&'a Id>,
        decision: for<'a> fn(&'a Decision) -> Option<&'a Id>,
    },
}
#[derive(Clone, Copy)]
pub(crate) struct Field {
    pub name: &'static str,
    pub label: &'static str,
    pub table: FieldScope,
    pub level: Level,
    pub shape: Shape,
    pub presence: Presence,
    pub reference: Option<ReferenceAccess>,
}
