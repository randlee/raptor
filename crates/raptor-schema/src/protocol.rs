use serde::Serialize;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
pub enum MetaLevel {
    Header,
    Item,
    Section,
    Label,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
pub enum MetaShape {
    Text,
    Date,
    Version,
    Status,
    Id,
    IdList,
    TextList,
    StatementList,
    Checklist,
    LinkList,
    Group,
    Derived,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Role {
    HeadingId,
    HeadingTitle,
    ItemLabel,
    HeaderLabel,
    SectionLabel,
    Group,
    SectionProse,
}
