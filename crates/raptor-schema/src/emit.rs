use crate::{accept::ErrorTable, metadata::*, schema::*};
use schemars::{JsonSchema, schema::RootSchema, schema_for};
use serde::Serialize;
use std::collections::{BTreeMap, BTreeSet};

/// Every `ErrorTable` variant must have exactly one entry in this table.
pub const TABLES: [(&str, ErrorTable); 2] = [
    ("requirements", ErrorTable::Req),
    ("decisions", ErrorTable::Dec),
];
const fn table_count(table: ErrorTable) -> usize {
    match table {
        ErrorTable::Req => 1,
        ErrorTable::Dec => 1,
    }
}
const _: () = assert!(TABLES.len() == table_count(ErrorTable::Req) + table_count(ErrorTable::Dec));
#[derive(Serialize)]
pub struct FieldMeta {
    pub name: &'static str,
    pub label: &'static str,
    pub table: &'static str,
    pub level: &'static str,
    pub shape: &'static str,
    pub section: Option<&'static str>,
    pub modal: Option<Modal>,
    pub required: bool,
    pub nullable: bool,
    pub sql_type: &'static str,
    pub role: &'static str,
}

fn binding(level: Level, shape: Shape) -> (&'static str, &'static str, Option<Modal>) {
    use Shape::*;
    let (shape_name, modal) = match shape {
        Text => ("Text", None),
        Date => ("Date", None),
        Version => ("Version", None),
        Status => ("Status", None),
        Id => ("Id", None),
        IdList => ("IdList", None),
        TextList => ("TextList", None),
        StatementList => ("StatementList", None),
        Statements(modal) => ("StatementList", Some(modal)),
        Checklist => ("Checklist", None),
        LinkList => ("LinkList", None),
        Group => ("Group", None),
        Derived => ("Derived", None),
    };
    let role = match (level, shape) {
        (Level::Item, Id) => "heading_id",
        (Level::Item, Text) => "heading_title",
        (
            Level::Item,
            Date | Version | Status | IdList | TextList | StatementList | Statements(_) | Checklist
            | LinkList | Group | Derived,
        ) => "item_label",
        (Level::Header, _) => "header_label",
        (Level::Label(_), _) => "section_label",
        (Level::Section, Group) => "group",
        (
            Level::Section,
            Text | Date | Version | Status | Id | IdList | TextList | StatementList | Statements(_)
            | Checklist | LinkList | Derived,
        ) => "section_prose",
    };
    (role, shape_name, modal)
}

pub fn field_table(table: Table) -> Vec<FieldMeta> {
    FIELDS
        .iter()
        .filter(|field| field.2 == Table::Both || field.2 == table)
        .map(|field| {
            let &(name, label, scope, level, shape, presence) = field;
            let (role, shape, modal) = binding(level, shape);
            let (level, section) = match level {
                Level::Header => ("Header", None),
                Level::Item => ("Item", None),
                Level::Section => ("Section", None),
                Level::Label(section) => ("Label", Some(section.heading())),
            };
            FieldMeta {
                name,
                label,
                level,
                shape,
                section,
                modal,
                role,
                table: match scope {
                    Table::Req => "Req",
                    Table::Dec => "Dec",
                    Table::Both => "Both",
                },
                required: presence == Presence::Required,
                nullable: presence == Presence::Nullable,
                sql_type: "TEXT",
            }
        })
        .collect()
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

pub fn json_schema() -> Result<BTreeMap<&'static str, RootSchema>, serde_json::Error> {
    let mut schemas = BTreeMap::new();
    for (name, table, mut schema) in [
        ("requirements", Table::Req, schema_for!(Requirement)),
        ("decisions", Table::Dec, schema_for!(Decision)),
    ] {
        schema
            .schema
            .extensions
            .insert("x-raptor-fields".into(), serde_json::to_value(field_table(table))?);
        let kinds = record_kinds(table);
        schema
            .schema
            .extensions
            .insert("x-raptor-kinds".into(), serde_json::to_value(kinds)?);
        schemas.insert(name, schema);
    }
    Ok(schemas)
}

pub fn sql_ddl() -> String {
    let mut statements = Vec::new();
    let mut edges = Vec::new();
    let status_values = enum_values::<Status>();
    for (table, kind) in TABLES {
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
                field.level != "Label" && field.shape != "Derived" && seen.insert(field.name)
            })
            .map(|field| {
                let check = if field.role == "heading_id" {
                    sql_check(&id_prefixes, |values| {
                        format!("substr({}, 1, {}) IN ({values})", field.name, prefix_width)
                    })
                } else if field.shape == "Status" {
                    sql_check(&status_values, |values| format!("{} IN ({values})", field.name))
                } else {
                    String::new()
                };
                let constraint = if field.role == "heading_id" {
                    format!(" NOT NULL PRIMARY KEY{check}")
                } else if field.nullable {
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
            .filter(|field| field.shape == "IdList" && field.level == "Label")
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
    statements.push(format!("CREATE VIEW edges AS {};", edges.join(" UNION ALL ")));
    statements.join("\n")
}
