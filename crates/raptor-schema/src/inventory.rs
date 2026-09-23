use crate::{
    accept::{Batch, Error, ErrorCategory},
    schema::*,
};
use serde::Serialize;
use std::collections::BTreeMap;

#[derive(Debug, PartialEq, Eq, PartialOrd, Ord, Serialize)]
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

fn references<'a>(
    lifecycle: &'a Lifecycle,
    related: &'a RelatedDocuments,
    dependencies: Option<&'a Dependencies>,
) -> Vec<(&'static str, Option<usize>, &'a Id)> {
    let mut groups = vec![
        ("/related_documents/requirements", related.requirements.as_slice()),
        ("/related_documents/architecture_decisions", related.architecture_decisions.as_slice()),
    ];
    if let Some(dependencies) = dependencies {
        groups.extend([
            ("/dependencies/requires", dependencies.requires.as_slice()),
            ("/dependencies/related", dependencies.related.as_slice()),
        ]);
    }
    groups
        .into_iter()
        .flat_map(|(path, items)| {
            items
                .iter()
                .enumerate()
                .map(move |(index, item)| (path, Some(index), &item.id))
        })
        .chain(
            [
                ("/supersedes", lifecycle.supersedes.as_ref()),
                ("/superseded_by", lifecycle.superseded_by.as_ref()),
            ]
            .into_iter()
            .filter_map(|(path, target)| target.map(|id| (path, None, id))),
        )
        .collect()
}

pub fn check_inventory(batch: &Batch) -> Vec<Error> {
    let requirements = batch.requirements().map(|(position, row)| {
        let targets = references(&row.lifecycle, &row.related_documents, Some(&row.dependencies));
        ("requirements", position, &row.identity, targets)
    });
    let decisions = batch.decisions().map(|(position, row)| {
        let targets = references(&row.lifecycle, &row.related_documents, None);
        ("decisions", position, &row.identity, targets)
    });
    let rows: Vec<_> = requirements.chain(decisions).collect();
    let mut counts = BTreeMap::new();
    for (_, _, identity, _) in &rows {
        *counts.entry(identity.id.as_str()).or_insert(0usize) += 1;
    }
    let mut errors = Vec::new();
    for (table, position, identity, targets) in rows {
        let error = |category, text, path, item| {
            let mut error = Error::scalar(category, text).at(path, item);
            error.table = Some(table.into());
            error.record_position = Some(position);
            error
        };
        if counts
            .get(identity.id.as_str())
            .is_some_and(|count| *count > 1)
        {
            errors.push(error(ErrorCategory::DuplicateId, identity.id.as_str(), "/id", None));
        }
        for (path, item, target) in targets {
            if !counts.contains_key(target.as_str()) {
                errors.push(error(ErrorCategory::DanglingReference, target.as_str(), path, item));
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
        let rule = match error.category {
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
        };
        *counts.entry(rule).or_insert(0) += 1;
    }
    Summary {
        records: batch.requirements().count() + batch.decisions().count(),
        counts,
    }
}
