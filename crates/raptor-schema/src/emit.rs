use crate::{error::TableId, fields::FIELDS, metadata::*, schema::*};
use schemars::{JsonSchema, schema::RootSchema, schema_for};
use serde::Serialize;
use std::collections::{BTreeMap, BTreeSet};

pub use crate::protocol::{MetaLevel, MetaShape, Role};
/// Public projection of a field; the backing catalog is crate-internal.
///
/// ```compile_fail
/// use raptor_schema::FIELDS;
/// ```
#[derive(Serialize)]
pub struct FieldMeta {
    pub name: &'static str,
    pub label: &'static str,
    pub table: FieldScope,
    pub level: MetaLevel,
    /// Markdown source-interpretation shape; stored structure is in JSON Schema.
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
        (
            Level::Header,
            Text | Date | Version | Status | Id | Supersession | IdList | TextList | StatementList
            | Statements(_) | Checklist | LinkList | Group | Derived,
        ) => Role::HeaderLabel,
        (
            Level::Label(_),
            Text | Date | Version | Status | Id | Supersession | IdList | TextList | StatementList
            | Statements(_) | Checklist | LinkList | Group | Derived,
        ) => Role::SectionLabel,
        (Level::Section, Group) => Role::Group,
        (
            Level::Section,
            Text | Date | Version | Status | Id | Supersession | IdList | TextList | StatementList
            | Statements(_) | Checklist | LinkList | Derived,
        ) => Role::SectionProse,
    };
    (role, shape_name, modal)
}

pub fn field_table(table: TableId) -> Vec<FieldMeta> {
    FIELDS
        .iter()
        .filter(|field| field.table == FieldScope::All || field.table == FieldScope::Only(table))
        .map(|field| {
            let Field {
                name,
                label,
                table: scope,
                level,
                shape,
                presence,
                reference: _,
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
                sql_type: shape_source.sql_type(),
            }
        })
        .collect()
}

fn field_json(field: &FieldMeta) -> serde_json::Value {
    let table = field.table.wire_name();
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

fn id_prefix_check(field: &str, prefixes: &[String]) -> String {
    let mut groups = BTreeMap::<usize, Vec<String>>::new();
    for prefix in prefixes {
        groups
            .entry(prefix.len())
            .or_default()
            .push(sql_literal(prefix));
    }
    if groups.is_empty() {
        return " CHECK (0)".to_owned();
    }
    let choices = groups
        .into_iter()
        .map(|(width, literals)| {
            format!("substr({field}, 1, {width}) IN ({})", literals.join(", "))
        })
        .collect::<Vec<_>>();
    format!(" CHECK ({})", choices.join(" OR "))
}

pub(crate) fn table_schema(kind: TableId) -> RootSchema {
    let table = kind;
    let mut schema = match kind {
        TableId::Req => schema_for!(Requirement),
        TableId::Dec => schema_for!(Decision),
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
    schema
        .schema
        .extensions
        .insert("x-raptor-protocol".into(), crate::boundary::protocol());
    for definition in schema.definitions.values_mut() {
        if let schemars::schema::Schema::Object(object) = definition
            && let Some(properties) = &object.object
        {
            let roles = properties
                .properties
                .keys()
                .filter_map(|key| {
                    let role = crate::boundary::semantic_role(key)?;
                    Some((role.to_owned(), serde_json::Value::String(key.clone())))
                })
                .collect();
            object
                .extensions
                .insert("x-raptor-roles".into(), serde_json::Value::Object(roles));
        }
    }
    crate::schema_contract::apply(&mut schema);
    schema
}

/// Emit structural schemas; Id, Version and Date semantics are enforced by
/// `validate_scalar` and `accept`, rather than by a second schema grammar.
pub fn json_schema() -> BTreeMap<&'static str, RootSchema> {
    TableId::ALL
        .into_iter()
        .map(|kind| (kind.name(), table_schema(kind)))
        .collect()
}

pub fn sql_ddl() -> String {
    let mut statements = Vec::new();
    let mut edges = Vec::new();
    let status_values = enum_values::<Status>();
    for kind in TableId::ALL {
        let table = kind.name();
        let fields = field_table(kind);
        let id_prefixes = record_kinds(kind)
            .iter()
            .map(|kind| kind.prefix().to_owned())
            .collect::<Vec<_>>();
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
                    id_prefix_check(field.name, &id_prefixes)
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

#[cfg(test)]
mod tests;
