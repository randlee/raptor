//! Schema extensions used by source-language adapters.
use serde_json::{Value, json};

fn categories(rule: crate::inventory::Rule) -> Value {
    Value::Array(
        crate::error::ErrorCategory::ALL
            .into_iter()
            .filter(|category| category.rule() == rule)
            .map(|category| json!(category))
            .collect(),
    )
}
pub(crate) fn rules() -> Value {
    use crate::inventory::Rule;
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
    json!({
        "requirements": {
            "template": "record", "heading_label": "Requirement", "heading_range_label": range,
            "group_heading_prefix": "Alternative", "range_separator": " through "
        },
        "decisions": {
            "template": "record", "heading_label": "Decision", "heading_range_label": range,
            "group_heading_prefix": "Alternative", "range_separator": " through "
        }
    })
}
