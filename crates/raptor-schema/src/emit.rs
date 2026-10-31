use crate::{error::ErrorTable, fields::FIELDS, metadata::*, schema::*};
use schemars::{JsonSchema, schema::RootSchema, schema_for};
use serde::Serialize;
use std::collections::{BTreeMap, BTreeSet};

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
#[derive(Serialize)]
pub struct FieldMeta {
    pub name: &'static str,
    pub label: &'static str,
    pub table: Table,
    pub level: MetaLevel,
    pub shape: MetaShape,
    pub section: Option<&'static str>,
    pub modal: Option<Modal>,
    pub modal_label_suffix: Option<&'static str>,
    pub required: bool,
    pub nullable: bool,
    pub supersession: bool,
    pub sql_type: &'static str,
    pub role: Role,
}

fn binding(level: Level, shape: Shape) -> (Role, MetaShape, Option<Modal>) {
    use Shape::*;
    let (shape_name, modal) = match shape {
        Text => (MetaShape::Text, None),
        Date => (MetaShape::Date, None),
        Version => (MetaShape::Version, None),
        Status => (MetaShape::Status, None),
        Id | Supersession => (MetaShape::Id, None),
        IdList => (MetaShape::IdList, None),
        TextList => (MetaShape::TextList, None),
        StatementList => (MetaShape::StatementList, None),
        Statements(modal) => (MetaShape::StatementList, Some(modal)),
        Checklist => (MetaShape::Checklist, None),
        LinkList => (MetaShape::LinkList, None),
        Group => (MetaShape::Group, None),
        Derived => (MetaShape::Derived, None),
    };
    let role = match (level, shape) {
        (Level::Item, Id) => Role::HeadingId,
        (Level::Item, Text) => Role::HeadingTitle,
        (
            Level::Item,
            Date | Version | Status | Supersession | IdList | TextList | StatementList
            | Statements(_) | Checklist | LinkList | Group | Derived,
        ) => Role::ItemLabel,
        (Level::Header, _) => Role::HeaderLabel,
        (Level::Label(_), _) => Role::SectionLabel,
        (Level::Section, Group) => Role::Group,
        (
            Level::Section,
            Text | Date | Version | Status | Id | Supersession | IdList | TextList | StatementList
            | Statements(_) | Checklist | LinkList | Derived,
        ) => Role::SectionProse,
    };
    (role, shape_name, modal)
}

pub fn field_table(table: Table) -> Vec<FieldMeta> {
    FIELDS
        .iter()
        .filter(|field| field.table == Table::Both || field.table == table)
        .map(|field| {
            let Field {
                name,
                label,
                table: scope,
                level,
                shape,
                presence,
            } = *field;
            let shape_source = shape;
            let (role, shape, modal) = binding(level, shape);
            let (level, section) = match level {
                Level::Header => (MetaLevel::Header, None),
                Level::Item => (MetaLevel::Item, None),
                Level::Section => (MetaLevel::Section, None),
                Level::Label(section) => (MetaLevel::Label, Some(section.heading())),
            };
            FieldMeta {
                name,
                label,
                level,
                shape,
                section,
                modal,
                modal_label_suffix: modal.and_then(|_| label.find(' ').map(|i| &label[i..])),
                role,
                table: scope,
                required: presence == Presence::Required,
                nullable: presence == Presence::Nullable,
                supersession: shape_source == Shape::Supersession,
                sql_type: "TEXT",
            }
        })
        .collect()
}

fn field_json(field: &FieldMeta) -> serde_json::Value {
    let table = match field.table {
        Table::Req => "Req",
        Table::Dec => "Dec",
        Table::Both => "Both",
    };
    let level = match field.level {
        MetaLevel::Header => "Header",
        MetaLevel::Item => "Item",
        MetaLevel::Section => "Section",
        MetaLevel::Label => "Label",
    };
    let shape = match field.shape {
        MetaShape::Text => "Text",
        MetaShape::Date => "Date",
        MetaShape::Version => "Version",
        MetaShape::Status => "Status",
        MetaShape::Id => "Id",
        MetaShape::IdList => "IdList",
        MetaShape::TextList => "TextList",
        MetaShape::StatementList => "StatementList",
        MetaShape::Checklist => "Checklist",
        MetaShape::LinkList => "LinkList",
        MetaShape::Group => "Group",
        MetaShape::Derived => "Derived",
    };
    let role = match field.role {
        Role::HeadingId => "heading_id",
        Role::HeadingTitle => "heading_title",
        Role::ItemLabel => "item_label",
        Role::HeaderLabel => "header_label",
        Role::SectionLabel => "section_label",
        Role::Group => "group",
        Role::SectionProse => "section_prose",
    };
    let modal = field.modal.map(|modal| match modal {
        Modal::Must => "Must",
        Modal::Should => "Should",
        Modal::MustNot => "MustNot",
    });
    serde_json::json!({
        "name": field.name, "label": field.label, "table": table, "level": level,
        "shape": shape, "section": field.section, "modal": modal,
        "modal_label_suffix": field.modal_label_suffix, "required": field.required,
        "nullable": field.nullable, "supersession": field.supersession,
        "sql_type": field.sql_type, "role": role
    })
}

fn record_kinds(table: Table) -> &'static [RecordKind] {
    match table {
        Table::Req => &[RecordKind::Req, RecordKind::Nfr],
        Table::Dec => &[RecordKind::Adr],
        Table::Both => &[],
    }
}

fn enum_values<T: JsonSchema>() -> Vec<String> {
    schema_for!(T)
        .schema
        .enum_values
        .unwrap_or_default()
        .into_iter()
        .filter_map(|value| value.as_str().map(str::to_owned))
        .collect()
}

fn sql_literal(value: &str) -> String {
    format!("'{}'", value.replace('\'', "''"))
}

fn sql_check(values: &[String], expression: impl FnOnce(&str) -> String) -> String {
    if values.is_empty() {
        " CHECK (0)".to_owned()
    } else {
        let literals = values
            .iter()
            .map(|value| sql_literal(value))
            .collect::<Vec<_>>();
        format!(" CHECK ({})", expression(&literals.join(", ")))
    }
}

pub(crate) fn table_schema(kind: ErrorTable) -> RootSchema {
    let table = kind.into();
    let mut schema = match kind {
        ErrorTable::Req => schema_for!(Requirement),
        ErrorTable::Dec => schema_for!(Decision),
    };
    schema.schema.extensions.insert(
        "x-raptor-fields".into(),
        serde_json::Value::Array(field_table(table).iter().map(field_json).collect()),
    );
    let kinds = record_kinds(table);
    schema.schema.extensions.insert(
        "x-raptor-kinds".into(),
        serde_json::Value::Array(
            kinds
                .iter()
                .map(|kind| {
                    let name = match kind {
                        RecordKind::Req => "Req",
                        RecordKind::Nfr => "Nfr",
                        RecordKind::Adr => "Adr",
                    };
                    serde_json::Value::String(name.to_owned())
                })
                .collect(),
        ),
    );
    schema
        .schema
        .extensions
        .insert("x-raptor-rules".into(), crate::boundary::rules());
    schema
        .schema
        .extensions
        .insert("x-raptor-tables".into(), crate::boundary::tables());
    for definition in schema.definitions.values_mut() {
        if let schemars::schema::Schema::Object(object) = definition
            && let Some(properties) = &object.object
        {
            let roles = properties
                .properties
                .keys()
                .filter_map(|key| {
                    let role = match key.as_str() {
                        "text" => "content",
                        "checked" => "selection",
                        "id" => "identifier",
                        "href" => "destination",
                        "note" => "annotation",
                        "modal" => "modality",
                        "name" => "caption",
                        "groups" => "collection",
                        _ => return None,
                    };
                    Some((role.to_owned(), serde_json::Value::String(key.clone())))
                })
                .collect();
            object
                .extensions
                .insert("x-raptor-roles".into(), serde_json::Value::Object(roles));
        }
    }
    schema
}

pub fn json_schema() -> BTreeMap<&'static str, RootSchema> {
    ErrorTable::ALL
        .into_iter()
        .map(|kind| (kind.name(), table_schema(kind)))
        .collect()
}

pub fn sql_ddl() -> String {
    let mut statements = Vec::new();
    let mut edges = Vec::new();
    let status_values = enum_values::<Status>();
    for kind in ErrorTable::ALL {
        let table = kind.name();
        let fields = field_table(kind.into());
        let id_prefixes = record_kinds(kind.into())
            .iter()
            .filter_map(|kind| {
                serde_json::to_value(kind)
                    .ok()
                    .and_then(|value| value.as_str().map(str::to_owned))
                    .map(|value| format!("{}-", value.to_ascii_uppercase()))
            })
            .collect::<Vec<_>>();
        let prefix_width = id_prefixes
            .iter()
            .map(String::len)
            .max()
            .unwrap_or_default();
        let mut seen = BTreeSet::new();
        let columns: Vec<_> = fields
            .iter()
            .filter(|field| {
                field.level != MetaLevel::Label
                    && field.shape != MetaShape::Derived
                    && seen.insert(field.name)
            })
            .map(|field| {
                let check = if field.role == Role::HeadingId {
                    sql_check(&id_prefixes, |values| {
                        format!("substr({}, 1, {}) IN ({values})", field.name, prefix_width)
                    })
                } else if field.shape == MetaShape::Status {
                    sql_check(&status_values, |values| {
                        format!("{} IN ({values})", field.name)
                    })
                } else {
                    String::new()
                };
                let constraint = if field.role == Role::HeadingId {
                    format!(" NOT NULL PRIMARY KEY{check}")
                } else if field.supersession {
                    format!(" REFERENCES {table}(id) DEFERRABLE INITIALLY DEFERRED")
                } else {
                    format!(" NOT NULL{check}")
                };
                format!("{} {}{}", field.name, field.sql_type, constraint)
            })
            .collect();
        statements.push(format!("CREATE TABLE {table} ({});", columns.join(", ")));
        for field in fields
            .iter()
            .filter(|field| field.shape == MetaShape::IdList && field.level == MetaLevel::Label)
        {
            if let Some(parent) = fields
                .iter()
                .find(|parent| Some(parent.label) == field.section)
            {
                let path = format!("{}.{}", parent.name, field.name);
                edges.push(format!(
                    "SELECT r.id AS source, '{path}' AS path, \
                     json_extract(j.value, '$.id') AS target, \
                     j.key AS position FROM {table} r, json_each(r.{}, '$.{}') j",
                    parent.name, field.name
                ));
            }
        }
    }
    statements.push(format!(
        "CREATE VIEW edges AS {};",
        edges.join(" UNION ALL ")
    ));
    statements.join("\n")
}
