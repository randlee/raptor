//! Schema extensions used by source-language adapters.
use serde_json::{Value, json};

const SEMANTIC_ROLES: [(&str, &str); 8] = [
    ("content", "text"),
    ("selection", "checked"),
    ("identifier", "id"),
    ("destination", "href"),
    ("annotation", "note"),
    ("modality", "modal"),
    ("caption", "name"),
    ("collection", "groups"),
];
pub(crate) fn semantic_role(property: &str) -> Option<&'static str> {
    SEMANTIC_ROLES
        .iter()
        .find(|(_, field)| *field == property)
        .map(|(role, _)| *role)
}
pub(crate) fn protocol() -> Value {
    use crate::protocol::{MetaLevel as L, MetaShape as S, Role as R};
    json!({
        "levels": [L::Header, L::Item, L::Section, L::Label],
        "shapes": [S::Text, S::Date, S::Version, S::Status, S::Id, S::IdList, S::TextList,
                   S::StatementList, S::Checklist, S::LinkList, S::Group, S::Derived],
        "roles": [R::HeadingId, R::HeadingTitle, R::ItemLabel, R::HeaderLabel,
                  R::SectionLabel, R::Group, R::SectionProse],
        "heading_roles": {"identifier": R::HeadingId, "caption": R::HeadingTitle},
        "semantic_roles": SEMANTIC_ROLES.iter().map(|(role, _)| *role).collect::<Vec<_>>()
    })
}

fn categories(rule: crate::rule::Rule) -> Value {
    Value::Array(
        crate::error::ErrorCategory::ALL
            .into_iter()
            .filter(|category| category.rule() == rule)
            .map(|category| json!(category))
            .collect(),
    )
}
pub(crate) fn rules() -> Value {
    use crate::rule::Rule;
    json!({
        "MISSING_ID": {
            "rejects_record": true, "remedy": "Add the required field.",
            "categories": categories(Rule::MissingId)
        },
        "MISSING_FIELD": {
            "rejects_record": true, "remedy": "Add the required field.",
            "categories": categories(Rule::MissingField)
        },
        "UNKNOWN_SECTION": {
            "rejects_record": false, "remedy": "Remove the section or use an allowed section.",
            "categories": categories(Rule::UnknownSection)
        },
        "UNKNOWN_LABEL": {
            "rejects_record": false, "remedy": "Remove the label or use an allowed label.",
            "categories": categories(Rule::UnknownLabel)
        },
        "BAD_VALUE": {
            "rejects_record": true, "remedy": "Use the documented value format.",
            "categories": categories(Rule::BadValue)
        },
        "DUPLICATE_ID": {
            "rejects_record": false, "remedy": "Make the identifier unique.",
            "categories": categories(Rule::DuplicateId)
        },
        "DANGLING_REFERENCE": {
            "rejects_record": false,
            "remedy": "Declare the referenced identifier or remove the reference.",
            "categories": categories(Rule::DanglingReference)
        }
    })
}
pub(crate) fn tables() -> Value {
    let range = crate::fields::FIELDS
        .iter()
        .find(|field| field.shape == crate::metadata::Shape::Derived)
        .map(|field| field.label);
    let tables = crate::error::TableId::ALL
        .into_iter()
        .map(|table| {
            let heading = match table {
                crate::error::TableId::Req => "Requirement",
                crate::error::TableId::Dec => "Decision",
            };
            let prefixes: Vec<_> = crate::schema::record_kinds(table)
                .iter()
                .map(|kind| kind.prefix())
                .collect();
            (
                table.name().to_owned(),
                json!({
                    "template": "record", "heading_label": heading, "heading_range_label": range,
                    "group_heading_prefix": "Alternative", "range_separator": " through ",
                    "id_prefixes": prefixes
                }),
            )
        })
        .collect();
    Value::Object(tables)
}
