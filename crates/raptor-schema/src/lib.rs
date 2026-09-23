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
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct Lifecycle { pub status: Status, pub version: Version, pub created: Date, pub last_updated: Date, pub owner: String }
#[rustfmt::skip]
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct Requirement { #[serde(flatten)] pub identity: Identity, #[serde(flatten)] pub lifecycle: Lifecycle }
#[rustfmt::skip]
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize, JsonSchema)] pub struct Decision { #[serde(flatten)] pub identity: Identity, #[serde(flatten)] pub lifecycle: Lifecycle }
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
#[rustfmt::skip] impl HasIdentity for Requirement { fn identity(&self) -> &Identity { &self.identity } }
#[rustfmt::skip] impl HasIdentity for Decision { fn identity(&self) -> &Identity { &self.identity } }
#[rustfmt::skip] impl HasLifecycle for Requirement { fn lifecycle(&self) -> &Lifecycle { &self.lifecycle } }
#[rustfmt::skip] impl HasLifecycle for Decision { fn lifecycle(&self) -> &Lifecycle { &self.lifecycle } }
#[rustfmt::skip]
const FIELDS: &[FieldMeta] = &[
    FieldMeta{name:"id",label:"ID",level:Level::Item,shape:Shape::Id,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"title",label:"Title",level:Level::Item,shape:Shape::Text,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"status",label:"Status",level:Level::Header,shape:Shape::Status,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"version",label:"Version",level:Level::Header,shape:Shape::Version,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"created",label:"Created",level:Level::Header,shape:Shape::Date,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"last_updated",label:"Last Updated",level:Level::Header,shape:Shape::Date,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"owner",label:"Owner",level:Level::Header,shape:Shape::Text,section:None,required:true,sql_type:"TEXT"}, FieldMeta{name:"id_range",label:"ID Range",level:Level::Header,shape:Shape::Derived,section:None,required:false,sql_type:"TEXT"}, FieldMeta{name:"status",label:"Status",level:Level::Item,shape:Shape::Status,section:None,required:true,sql_type:"TEXT"},
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
#[rustfmt::skip] fn details(rule: &Rule) -> (&'static str, &'static str) { match rule { Rule::MissingId | Rule::MissingField => MISSING, Rule::BadValue => BAD, Rule::UnknownSection => UNKNOWN_SECTION, Rule::UnknownLabel => UNKNOWN_LABEL, Rule::DuplicateId => DUPLICATE } }
fn diagnostic(
    file: &str,
    line: u32,
    rule: Rule,
    id: Option<Id>,
    label: Option<String>,
    pair: (&'static str, &'static str),
) -> Diagnostic {
    Diagnostic {
        file: file.into(),
        line,
        rule,
        id,
        label,
        message: pair.0,
        allowed: None,
        remedy: pair.1,
    }
}
#[rustfmt::skip] fn string(tree: &serde_json::Value, key: &str) -> Option<String> { let value = tree.get(key)?; value.as_str().or_else(|| value.get("value").and_then(|v| v.as_str())).map(str::to_owned) }
fn tree_line(tree: &serde_json::Value) -> u32 {
    tree.get("line").and_then(|v| v.as_u64()).unwrap_or(0) as u32
}
fn allowed(level: Level) -> Vec<String> {
    FIELDS
        .iter()
        .filter(|f| f.level == level)
        .map(|f| f.label.into())
        .collect()
}
fn unknown(
    file: &str,
    line: u32,
    rule: Rule,
    id: Option<Id>,
    label: String,
    allowed: Vec<String>,
) -> Diagnostic {
    let pair = if rule == Rule::UnknownSection {
        UNKNOWN_SECTION
    } else {
        UNKNOWN_LABEL
    };
    let mut out = diagnostic(file, line, rule, id, Some(label), pair);
    out.allowed = Some(allowed);
    out
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
            .push(diagnostic(file, 0, Rule::MissingId, None, None, MISSING));
    }
    for (name, value) in header.as_object().into_iter().flatten() {
        if !FIELDS
            .iter()
            .any(|f| f.level == Level::Header && f.label == name)
        {
            out.diagnostics.push(unknown(
                file,
                tree_line(value),
                Rule::UnknownLabel,
                None,
                name.clone(),
                allowed(Level::Header),
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
        if raw_id.is_none() {
            out.diagnostics
                .push(diagnostic(file, line, Rule::MissingId, None, None, MISSING));
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
                    BAD,
                ));
                continue;
            }
        };
        for (name, value) in fields.as_object().into_iter().flatten() {
            if name != FIELDS[2].label {
                out.diagnostics.push(unknown(
                    file,
                    tree_line(value),
                    Rule::UnknownLabel,
                    Some(id.clone()),
                    name.clone(),
                    allowed(Level::Item),
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
            out.diagnostics.push(unknown(
                file,
                tree_line(section),
                Rule::UnknownSection,
                Some(id.clone()),
                name,
                vec![],
            ));
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
                out.diagnostics.push(unknown(
                    file,
                    tree_line(label),
                    Rule::UnknownLabel,
                    Some(id.clone()),
                    name,
                    vec![],
                ));
            }
        }
        if title.is_none()
            || status.is_none()
            || version.is_none()
            || created.is_none()
            || last_updated.is_none()
            || owner.is_none()
        {
            out.diagnostics.push(diagnostic(
                file,
                line,
                Rule::MissingField,
                Some(id),
                None,
                MISSING,
            ));
            continue;
        }
        let parsed = (
            serde_json::from_str(&format!("\"{}\"", status.unwrap())).ok(),
            version.unwrap().parse(),
            created.unwrap().parse(),
            last_updated.unwrap().parse(),
        );
        if let (Some(status), Ok(version), Ok(created), Ok(last_updated)) = parsed {
            let row = Lifecycle {
                status,
                version,
                created,
                last_updated,
                owner: owner.unwrap(),
            };
            let identity = Identity {
                id: id.clone(),
                title: title.unwrap(),
            };
            if identity.id.kind() == RecordKind::Adr {
                out.decisions.push(Decision {
                    identity,
                    lifecycle: row,
                })
            } else {
                out.requirements.push(Requirement {
                    identity,
                    lifecycle: row,
                })
            }
        } else {
            out.diagnostics
                .push(diagnostic(file, line, Rule::BadValue, Some(id), None, BAD));
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
    requirements
        .iter()
        .map(|x| &x.identity.id)
        .chain(decisions.iter().map(|x| &x.identity.id))
        .filter(|x| seen[&x.0] > 1)
        .map(|id| diagnostic("", 0, Rule::DuplicateId, Some(id.clone()), None, DUPLICATE))
        .collect()
}
pub fn field_table(table: &str) -> Vec<FieldMeta> {
    if matches!(table, "requirements" | "decisions") {
        FIELDS.to_vec()
    } else {
        vec![]
    }
}
pub fn sql_ddl() -> String {
    let mut names = HashSet::new();
    let columns = FIELDS
        .iter()
        .filter(|f| f.name != "id_range" && names.insert(f.name))
        .map(|f| format!("{} {} NOT NULL", f.name, f.sql_type))
        .collect::<Vec<_>>()
        .join(", ");
    let status = "'Draft','Proposed','Active','Approved','Deprecated','Superseded'";
    format!(
        "CREATE TABLE requirements ({columns}, PRIMARY KEY (id), CHECK (status IN ({status})), CHECK (id GLOB 'REQ-*' OR id GLOB 'NFR-*'));\nCREATE TABLE decisions ({columns}, PRIMARY KEY (id), CHECK (status IN ({status})), CHECK (id GLOB 'ADR-*'));\n"
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
