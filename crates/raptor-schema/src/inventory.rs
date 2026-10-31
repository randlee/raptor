use crate::{
    batch::Batch,
    error::{Error, ErrorCategory, ItemIndex, RecordPosition, TableId},
    fields::FIELDS,
    metadata::{FieldScope, Level, ReferenceAccess},
    rule::Rule,
    schema::*,
};
use serde::Serialize;
use std::collections::BTreeMap;

struct Reference<'a> {
    path: String,
    item: Option<ItemIndex>,
    target: &'a Id,
}
struct InventoryRow<'a> {
    table: TableId,
    position: RecordPosition,
    identity: &'a Identity,
    targets: Vec<Reference<'a>>,
}

pub(crate) struct IngressId<'a> {
    pub text: &'a str,
    pub validated: Option<&'a Id>,
}
pub(crate) struct IngressReference<'a> {
    pub text: &'a str,
    pub validated: Option<&'a Id>,
    pub path: String,
}
fn ingress_kind(text: &str, validated: Option<&Id>) -> Option<RecordKind> {
    validated
        .map(Id::kind)
        .or_else(|| RecordKind::from_id(text))
}
pub(crate) fn supersession_errors(
    source: Option<IngressId<'_>>,
    targets: &[IngressReference<'_>],
) -> Vec<Error> {
    let source = source.and_then(|id| ingress_kind(id.text, id.validated));
    targets
        .iter()
        .filter_map(|target| {
            let (source, target_kind) = source.zip(ingress_kind(target.text, target.validated))?;
            cross_kind(source, target_kind, target.text, &target.path)
        })
        .collect()
}
fn cross_kind(source: RecordKind, target: RecordKind, text: &str, path: &str) -> Option<Error> {
    (source != target).then(|| {
        Error::scalar(
            ErrorCategory::CrossKindSupersession,
            text,
            &format!("a {source:?} identifier, not {target:?}"),
        )
        .at(path, None)
    })
}

pub(crate) enum IncomingRow<'a> {
    Requirement(&'a Requirement),
    Decision(&'a Decision),
}
pub(crate) fn typed_supersession_errors(row: IncomingRow<'_>) -> Vec<Error> {
    let (kind, table) = match &row {
        IncomingRow::Requirement(row) => (row.identity.id.kind(), TableId::Req),
        IncomingRow::Decision(row) => (row.identity.id.kind(), TableId::Dec),
    };
    FIELDS
        .iter()
        .filter_map(|field| {
            if field.table != FieldScope::All && field.table != FieldScope::Only(table) {
                return None;
            }
            let target = match (field.reference, &row) {
                (
                    Some(ReferenceAccess::Scalar { requirement, .. }),
                    IncomingRow::Requirement(row),
                ) => requirement(row),
                (Some(ReferenceAccess::Scalar { decision, .. }), IncomingRow::Decision(row)) => {
                    decision(row)
                }
                _ => None,
            }?;
            cross_kind(
                kind,
                target.kind(),
                target.as_str(),
                &format!("/{}", field.name),
            )
        })
        .collect()
}

enum Source<'a> {
    Requirement(&'a Requirement),
    Decision(&'a Decision),
}

fn references(source: Source<'_>, table: TableId) -> Vec<Reference<'_>> {
    let mut references = Vec::new();
    let mut fields: Vec<_> = FIELDS
        .iter()
        .enumerate()
        .filter(|(_, field)| {
            field.reference.is_some()
                && (field.table == FieldScope::All || field.table == FieldScope::Only(table))
        })
        .collect();
    fields.sort_by_key(|(index, field)| {
        let section = match field.level {
            Level::Label(section) => FIELDS
                .iter()
                .position(|parent| {
                    parent.level == Level::Section && parent.label == section.heading()
                })
                .unwrap_or(0),
            _ => 0,
        };
        (
            matches!(field.reference, Some(ReferenceAccess::Scalar { .. })),
            std::cmp::Reverse(section),
            *index,
        )
    });
    for (_, field) in fields {
        match (field.reference, &source) {
            (Some(ReferenceAccess::Scalar { requirement, .. }), Source::Requirement(row)) => {
                if let Some(target) = requirement(row) {
                    references.push(Reference {
                        path: format!("/{}", field.name),
                        item: None,
                        target,
                    });
                }
            }
            (Some(ReferenceAccess::Scalar { decision, .. }), Source::Decision(row)) => {
                if let Some(target) = decision(row) {
                    references.push(Reference {
                        path: format!("/{}", field.name),
                        item: None,
                        target,
                    });
                }
            }
            (Some(ReferenceAccess::List { requirement, .. }), Source::Requirement(row)) => {
                append_list(&mut references, field, requirement(row));
            }
            (
                Some(ReferenceAccess::List {
                    decision: Some(decision),
                    ..
                }),
                Source::Decision(row),
            ) => {
                append_list(&mut references, field, decision(row));
            }
            _ => {}
        }
    }
    references
}

fn append_list<'a>(
    references: &mut Vec<Reference<'a>>,
    field: &crate::metadata::Field,
    items: &'a [IdItem],
) {
    if let Level::Label(section) = field.level
        && let Some(parent) = FIELDS
            .iter()
            .find(|parent| parent.level == Level::Section && parent.label == section.heading())
    {
        let path = format!("/{}/{}", parent.name, field.name);
        references.extend(items.iter().enumerate().map(|(index, item)| Reference {
            path: path.clone(),
            item: Some(ItemIndex(index)),
            target: &item.id,
        }));
    }
}

pub fn check_inventory(batch: &Batch) -> Vec<Error> {
    let requirements = batch.requirements().map(|entry| {
        let row = entry.value;
        let targets = references(Source::Requirement(row), TableId::Req);
        InventoryRow {
            table: TableId::Req,
            position: entry.position,
            identity: &row.identity,
            targets,
        }
    });
    let decisions = batch.decisions().map(|entry| {
        let row = entry.value;
        let targets = references(Source::Decision(row), TableId::Dec);
        InventoryRow {
            table: TableId::Dec,
            position: entry.position,
            identity: &row.identity,
            targets,
        }
    });
    let rows: Vec<_> = requirements.chain(decisions).collect();
    struct Occurrences {
        first: RecordPosition,
        count: usize,
    }
    let mut counts = BTreeMap::new();
    for row in &rows {
        let entry = counts
            .entry(row.identity.id.as_str())
            .or_insert(Occurrences {
                first: row.position,
                count: 0,
            });
        entry.count += 1;
    }
    let mut errors = Vec::new();
    for InventoryRow {
        table,
        position,
        identity,
        targets,
    } in rows
    {
        let error = |category, text, cause: String, path: &str, item| {
            let mut error = Error::scalar(category, text, &cause).at(path, item);
            error.table = Some(table);
            error.record_position = Some(position);
            error
        };
        if let Some(occurrences) = counts.get(identity.id.as_str())
            && occurrences.count > 1
        {
            let first_position = occurrences.first;
            let cause = format!(
                "a unique identifier; first occurrence is record position {}",
                first_position.0
            );
            let mut duplicate = error(
                ErrorCategory::DuplicateId,
                identity.id.as_str(),
                cause,
                "/id",
                None,
            );
            duplicate.set_first_occurrence(first_position);
            errors.push(duplicate);
        }
        for Reference { path, item, target } in targets {
            if !counts.contains_key(target.as_str()) {
                errors.push(error(
                    ErrorCategory::DanglingReference,
                    target.as_str(),
                    "a referenced record in the batch".into(),
                    &path,
                    item,
                ));
            }
        }
    }
    errors
}

#[derive(Serialize)]
pub struct Summary {
    pub records: usize,
    pub counts: BTreeMap<Rule, usize>,
}
pub fn summarize(batch: &Batch, errors: &[Error]) -> Summary {
    let mut counts = BTreeMap::new();
    for error in errors {
        let rule = error.category.rule();
        *counts.entry(rule).or_insert(0) += 1;
    }
    Summary {
        records: batch.requirements().count() + batch.decisions().count(),
        counts,
    }
}
