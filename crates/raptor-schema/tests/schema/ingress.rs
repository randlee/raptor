use super::common::{check_error, fixture};
use raptor_schema::*;
use serde_json::{Value, json};

fn reject(path: &str, value: Value, category: &str, item: Option<usize>) {
    let mut input = fixture();
    *input["requirements"][0].pointer_mut(path).unwrap() = value.clone();
    let result = accept(&input.to_string());
    assert_eq!(result.batch.requirements().count(), 0);
    assert_eq!(result.batch.decisions().count(), 1);
    assert_eq!(result.errors.len(), 1, "{:?}", result.errors);
    check_error(
        &result.errors[0],
        category,
        Some("requirements"),
        Some(0),
        path,
        item,
        &value,
    );
    if category == "CrossKindSupersession" {
        assert_eq!(
            result.errors[0].message.as_ref(),
            "Found \"ADR-FIX-0001\"; expected a Req identifier, not Adr."
        );
    }
    if category == "UnknownVariant" && path == "/status" {
        assert_eq!(
            result.errors[0].cause.as_ref(),
            "[\"Draft\",\"Proposed\",\"Active\",\"Approved\",\"Deprecated\",\"Superseded\"]"
        );
        assert!(
            result.errors[0]
                .message
                .contains(result.errors[0].cause.as_ref())
        );
        assert_eq!(
            serde_json::to_value(result.errors[0].allowed_values()).unwrap(),
            json!([
                "Draft",
                "Proposed",
                "Active",
                "Approved",
                "Deprecated",
                "Superseded"
            ])
        );
    }
    if category == "InvalidId" {
        assert_eq!(
            result.errors[0].cause.as_ref(),
            "an ID with REQ, NFR, or ADR prefix and four digits"
        );
        assert!(result.errors[0].allowed_values().is_none());
        assert!(
            result.errors[0]
                .first_occurrence_record_position()
                .is_none()
        );
    }
    let output = serde_json::to_value(&result).unwrap();
    assert_eq!(
        output["errors"][0]["recovery"],
        json!(result.errors[0].recovery)
    );
    if category == "InvalidId" {
        assert!(output["errors"][0]["allowed_values"].is_null());
        assert!(output["errors"][0]["first_occurrence_record_position"].is_null());
    }
    assert_eq!(output["summary"]["counts"], json!({"BAD_VALUE": 1}));
}
#[test]
fn serde_error_causes_preserve_real_failures() {
    let check = |value: Value, expected: &str, source: serde_json::Error| {
        let detail = source.to_string();
        let error = Error::from_serde(value.clone(), expected, source);
        assert_eq!(error.cause.as_ref(), format!("{expected} ({detail})"));
        assert_eq!(
            error.message.as_ref(),
            format!("Found {value}; expected {expected} ({detail}).")
        );
        error
    };
    for input in ["?", "{", "[1,]"] {
        let source = serde_json::from_str::<Value>(input).unwrap_err();
        let error = check(json!(input), "a JSON batch input", source);
        assert_eq!(json!(accept(input).errors[0]), json!(error));
    }
    assert_eq!(
        accept("?").errors[0].message.as_ref(),
        "Found \"?\"; expected a JSON batch input (expected value at line 1 column 1)."
    );
    for key in [vec![], vec![1], vec![1, 2]] {
        let map = std::collections::BTreeMap::from([(key, true)]);
        let source = serde_json::to_value(map).unwrap_err();
        check(Value::Null, "a serializable schema definition", source);
    }
    for value in [json!({}), json!({"id": 1}), json!({"id": "REQ-FIX-0001"})] {
        let source = serde_json::from_value::<Requirement>(value.clone()).unwrap_err();
        check(value, "a valid requirements record", source);
    }
}
#[test]
fn error_tables_reveal_wire_and_debug_identity() {
    let mut error = Error::new(ErrorCategory::TypeMismatch, Value::Null, "a record");
    for (table, kind, label, debug) in [
        (TableId::Req, TableId::Req, "requirements", "Some(Req)"),
        (TableId::Dec, TableId::Dec, "decisions", "Some(Dec)"),
    ] {
        error.table = Some(table);
        assert_eq!(json!(error.table), json!(label));
        assert_eq!(format!("{:?}", error.table), debug);
        assert!(table == kind);
    }
}
#[test]
fn valid_batch_preserves_records_and_checkbox_states() {
    for checked in [Value::Null, json!(false), json!(true)] {
        let mut input = fixture();
        input["requirements"][0]["success_criteria"]["acceptance_criteria"][0]["checked"] = checked;
        let result = accept(&input.to_string());
        assert!(result.errors.is_empty(), "{:?}", result.errors);
        let output = serde_json::to_value(result).unwrap();
        assert_eq!(output["batch"], input);
        assert_eq!(output["summary"], json!({"records": 2, "counts": {}}));
    }
}
#[test]
fn strict_values_have_structured_errors() {
    for (path, value, category, item) in [
        ("/title", json!([]), "TypeMismatch", None),
        ("/title", Value::Null, "NullNotAllowed", None),
        ("/status", json!("active"), "UnknownVariant", None),
        ("/status", json!("Actve"), "UnknownVariant", None),
        ("/id", json!("REQ-X-1"), "InvalidId", None),
        ("/version", json!("1.10.0"), "InvalidVersion", None),
        ("/created", json!("2026-13-01"), "InvalidDate", None),
        ("/created", json!("2025-02-29"), "InvalidDate", None),
        ("/created", json!("1900-02-29"), "InvalidDate", None),
        (
            "/supersedes",
            json!("ADR-FIX-0001"),
            "CrossKindSupersession",
            None,
        ),
        (
            "/requirement_statement/statements/0/modal",
            json!("must"),
            "UnknownVariant",
            Some(0),
        ),
    ] {
        reject(path, value, category, item);
    }
    for date in ["2000-02-29", "2024-02-29"] {
        let mut input = fixture();
        input["decisions"][0]["decision_date"] = json!(date);
        assert!(accept(&input.to_string()).errors.is_empty());
    }
}
#[test]
fn unknown_and_missing_keys_are_rejected_at_every_depth() {
    for (parent, key, item, missing) in [
        ("", "extra", None, false),
        (
            "/requirement_statement/statements/0",
            "extra",
            Some(0),
            false,
        ),
        ("", "owner", None, true),
        ("", "supersedes", None, true),
        ("", "superseded_by", None, true),
        (
            "/success_criteria/acceptance_criteria/0",
            "checked",
            Some(0),
            true,
        ),
    ] {
        let mut input = fixture();
        let object = input["requirements"][0]
            .pointer_mut(parent)
            .unwrap()
            .as_object_mut()
            .unwrap();
        let (category, value) = if missing {
            object.remove(key);
            ("MissingKey", Value::Null)
        } else {
            object.insert(key.into(), json!(42));
            ("UnknownKey", json!(42))
        };
        let result = accept(&input.to_string());
        assert_eq!(result.errors.len(), 1);
        assert_eq!(result.batch.requirements().count(), 0);
        let path = format!("{parent}/{key}");
        check_error(
            &result.errors[0],
            category,
            Some("requirements"),
            Some(0),
            &path,
            item,
            &value,
        );
        let output = serde_json::to_value(result).unwrap();
        assert_eq!(output["errors"][0]["table"], "requirements");
        assert_eq!(output["summary"]["counts"], json!({"BAD_VALUE": 1}));
    }
}

#[test]
fn malformed_batch_has_one_root_error() {
    for input in [
        json!(null),
        json!([]),
        json!({}),
        json!({"requirements": {}, "decisions": []}),
        json!({"requirements": [], "decisions": [], "extra": 1}),
    ] {
        let category = if input.get("extra").is_some() {
            "UnknownKey"
        } else {
            "TypeMismatch"
        };
        let result = accept(&input.to_string());
        assert_eq!(
            result.batch.requirements().count() + result.batch.decisions().count(),
            0
        );
        assert_eq!(result.errors.len(), 1);
        check_error(&result.errors[0], category, None, None, "", None, &input);
    }
    let result = accept("{");
    assert_eq!(result.errors.len(), 1);
    check_error(
        &result.errors[0],
        "TypeMismatch",
        None,
        None,
        "",
        None,
        &json!("{"),
    );
}

#[test]
fn mixed_batch_keeps_original_positions_and_collects_all_errors() {
    let mut input = fixture();
    let mut next = input["requirements"][0].clone();
    next["id"] = json!("REQ-FIX-0002");
    input["requirements"].as_array_mut().unwrap().push(next);
    input["requirements"][0]["title"] = Value::Null;
    let result = accept(&input.to_string());
    let positions = result.batch.requirements().map(|(position, _)| position);
    assert!(positions.eq([1]));
    assert_eq!(result.batch.decisions().count(), 1);
    assert_eq!(result.errors.len(), 1);
    check_error(
        &result.errors[0],
        "NullNotAllowed",
        Some("requirements"),
        Some(0),
        "/title",
        None,
        &Value::Null,
    );
    input["requirements"][0]["owner"] = json!(7);
    input["requirements"][0]["status"] = json!("active");
    let result = accept(&input.to_string());
    assert_eq!(result.errors.len(), 3);
    assert_eq!(
        serde_json::to_value(result).unwrap()["summary"]["counts"],
        json!({"BAD_VALUE": 3})
    );
}

#[test]
fn validated_ids_cache_kind_and_preserve_string_wire_format() {
    for (text, kind) in [
        ("REQ-FIX-0001", RecordKind::Req),
        ("NFR-FIX-0001", RecordKind::Nfr),
        ("ADR-FIX-0001", RecordKind::Adr),
    ] {
        let id = Id::try_from(text.to_owned()).unwrap();
        assert_eq!(id.kind(), kind);
        assert_eq!(id.as_str(), text);
        assert_eq!(serde_json::to_value(&id).unwrap(), json!(text));
        let decoded: Id = serde_json::from_value(json!(text)).unwrap();
        assert_eq!(decoded, id);
    }
    assert!(Id::try_from("REQ-X-1".to_owned()).is_err());
}

#[test]
fn errors_keep_typed_positions_and_bounded_size() {
    assert!(std::mem::size_of::<Error>() <= 128);
    let error = Error::new(ErrorCategory::TypeMismatch, json!(3), "a string")
        .at("/items/0", Some(ItemIndex(0)));
    assert_eq!(error.item_index(), Some(ItemIndex(0)));
    assert_eq!(serde_json::to_value(error).unwrap()["item_index"], 0);
}

#[test]
fn supersession_check_accumulates_with_other_invalid_fields() {
    let mut input = fixture();
    input["requirements"][0]["title"] = Value::Null;
    input["requirements"][0]["supersedes"] = json!("ADR-FIX-0001");
    let result = accept(&input.to_string());
    assert_eq!(result.batch.requirements().count(), 0);
    assert_eq!(result.errors.len(), 2);
    assert_eq!(result.errors[0].category, ErrorCategory::NullNotAllowed);
    assert_eq!(
        result.errors[1].category,
        ErrorCategory::CrossKindSupersession
    );
}
