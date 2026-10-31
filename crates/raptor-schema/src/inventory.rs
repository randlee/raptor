use crate::{
    batch::Batch,
    emit::{FieldMeta, MetaLevel, MetaShape, field_table},
    error::{Error, ErrorCategory, ErrorTable, RecordPosition},
    schema::*,
};
use serde::Serialize;
use std::collections::BTreeMap;

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize)]
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

impl ErrorCategory {
    pub(crate) fn rule(self) -> Rule {
        match self {
            ErrorCategory::DuplicateId => Rule::DuplicateId,
            ErrorCategory::DanglingReference => Rule::DanglingReference,
            ErrorCategory::UnknownKey
            | ErrorCategory::MissingKey
            | ErrorCategory::TypeMismatch
            | ErrorCategory::NullNotAllowed
            | ErrorCategory::InvalidId
            | ErrorCategory::InvalidDate
            | ErrorCategory::InvalidVersion
            | ErrorCategory::UnknownVariant
            | ErrorCategory::CrossKindSupersession => Rule::BadValue,
        }
    }
}

fn references<'a>(
    fields: &[FieldMeta],
    lifecycle: &'a Lifecycle,
    related: &'a RelatedDocuments,
    dependencies: Option<&'a Dependencies>,
) -> Vec<(String, Option<usize>, &'a Id)> {
    let mut references = Vec::new();
    // Traverse later sections first, retaining each section's label order and
    // handling supersession links after list references, as in the original wire order.
    let mut ordered: Vec<_> = fields
        .iter()
        .enumerate()
        .filter(|(_, field)| {
            field.supersession
                || (field.level == MetaLevel::Label && field.shape == MetaShape::IdList)
        })
        .collect();
    ordered.sort_by_key(|(index, field)| {
        let section = fields
            .iter()
            .position(|parent| {
                parent.level == MetaLevel::Section && Some(parent.label) == field.section
            })
            .unwrap_or(0);
        (field.supersession, std::cmp::Reverse(section), *index)
    });
    for (_, field) in ordered {
        if field.supersession {
            let target = match field.name {
                "supersedes" => lifecycle.supersedes.as_ref(),
                "superseded_by" => lifecycle.superseded_by.as_ref(),
                _ => None,
            };
            if let Some(target) = target {
                references.push((format!("/{}", field.name), None, target));
            }
        } else if field.level == MetaLevel::Label
            && field.shape == MetaShape::IdList
            && let Some(parent) = fields.iter().find(|parent| {
                Some(parent.label) == field.section && parent.level == MetaLevel::Section
            })
        {
            let items = match (parent.name, field.name) {
                ("related_documents", "requirements") => Some(related.requirements.as_slice()),
                ("related_documents", "architecture_decisions") => {
                    Some(related.architecture_decisions.as_slice())
                }
                ("dependencies", "requires") => dependencies.map(|value| value.requires.as_slice()),
                ("dependencies", "related") => dependencies.map(|value| value.related.as_slice()),
                _ => None,
            };
            if let Some(items) = items {
                let path = format!("/{}/{}", parent.name, field.name);
                references.extend(
                    items
                        .iter()
                        .enumerate()
                        .map(|(index, item)| (path.clone(), Some(index), &item.id)),
                );
            }
        }
    }
    references
}

pub fn check_inventory(batch: &Batch) -> Vec<Error> {
    let requirement_fields = field_table(ErrorTable::Req.into());
    let decision_fields = field_table(ErrorTable::Dec.into());
    let requirements = batch.requirements().map(|(position, row)| {
        let targets = references(
            &requirement_fields,
            &row.lifecycle,
            &row.related_documents,
            Some(&row.dependencies),
        );
        (ErrorTable::Req, position, &row.identity, targets)
    });
    let decisions = batch.decisions().map(|(position, row)| {
        let targets = references(
            &decision_fields,
            &row.lifecycle,
            &row.related_documents,
            None,
        );
        (ErrorTable::Dec, position, &row.identity, targets)
    });
    let rows: Vec<_> = requirements.chain(decisions).collect();
    let mut counts = BTreeMap::new();
    for (_, position, identity, _) in &rows {
        let entry = counts
            .entry(identity.id.as_str())
            .or_insert((*position, 0usize));
        entry.1 += 1;
    }
    let mut errors = Vec::new();
    for (table, position, identity, targets) in rows {
        let error = |category, text, cause: String, path: &str, item| {
            let mut error = Error::scalar(category, text, &cause).at(path, item);
            error.table = Some(table);
            error.record_position = Some(RecordPosition(position));
            error
        };
        if let Some((first_position, count)) = counts.get(identity.id.as_str())
            && *count > 1
        {
            let cause = format!(
                "a unique identifier; first occurrence is record position {first_position}"
            );
            let mut duplicate = error(
                ErrorCategory::DuplicateId,
                identity.id.as_str(),
                cause,
                "/id",
                None,
            );
            duplicate.set_first_occurrence(RecordPosition(*first_position));
            errors.push(duplicate);
        }
        for (path, item, target) in targets {
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
