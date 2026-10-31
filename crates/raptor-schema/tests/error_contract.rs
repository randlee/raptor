//! Public error and result serialization contracts, including a real failing output sink.
use raptor_schema::{Error, ErrorCategory, accept, validate_scalar};
use std::io::{self, Write};

struct UnavailableSink;
impl Write for UnavailableSink {
    fn write(&mut self, _: &[u8]) -> io::Result<usize> {
        Err(io::Error::other("output sink unavailable"))
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

#[test]
fn serialization_failure_preserves_structured_context_and_display() {
    let cause = serde_json::to_writer(UnavailableSink, &"payload").unwrap_err();
    let error = Error::serialization("JSON output", cause);
    assert_eq!(error.category, ErrorCategory::TypeMismatch);
    assert!(error.cause.contains("JSON output"));
    assert!(error.cause.contains("output sink unavailable"));
    assert!(!error.recovery.is_empty());
    let wire = serde_json::to_value(&error).unwrap();
    assert_eq!(wire.as_object().unwrap().len(), 11);
    assert_eq!(wire["message"], error.to_string());
    for field in [
        "table",
        "record_position",
        "item_index",
        "allowed_values",
        "first_occurrence_record_position",
        "offending_value",
    ] {
        assert!(wire[field].is_null(), "{field}");
    }
    assert!(serde_json::to_writer(UnavailableSink, &error).is_err());
}

#[test]
fn unknown_scalar_kind_is_a_structured_boundary_error() {
    let error = validate_scalar("UnrecognizedScalar", "opaque").unwrap_err();
    assert_eq!(error.category, ErrorCategory::UnknownVariant);
    assert_eq!(error.offending_value.as_str(), Some("UnrecognizedScalar"));
    assert!(!error.cause.is_empty());
    assert!(!error.recovery.is_empty());
}

#[test]
fn accepted_result_serialization_preserves_rows_without_internal_positions() {
    let source = include_str!("../../../tests/fixtures/records.json");
    let result = accept(source);
    let wire = serde_json::to_value(result).unwrap();
    assert_eq!(
        wire["batch"],
        serde_json::from_str::<serde_json::Value>(source).unwrap()
    );
    assert_eq!(wire["errors"], serde_json::json!([]));
    assert_eq!(
        wire["summary"],
        serde_json::json!({"records": 4, "counts": {}})
    );
    assert_eq!(wire.as_object().unwrap().len(), 3);
}

#[test]
fn invalid_supersession_id_still_accumulates_cross_kind_and_shape_errors() {
    let mut input: serde_json::Value =
        serde_json::from_str(include_str!("../../../tests/fixtures/records.json")).unwrap();
    input["requirements"].as_array_mut().unwrap().truncate(1);
    input["decisions"] = serde_json::json!([]);
    input["requirements"][0]["title"] = serde_json::Value::Null;
    input["requirements"][0]["supersedes"] = serde_json::json!("ADR-FIX-xxxx");
    let result = accept(&input.to_string());
    let categories: Vec<_> = result.errors.iter().map(|error| error.category).collect();
    assert_eq!(result.errors.len(), 3);
    for category in [
        ErrorCategory::NullNotAllowed,
        ErrorCategory::InvalidId,
        ErrorCategory::CrossKindSupersession,
    ] {
        assert!(categories.contains(&category), "{category:?}");
    }
    let wire = serde_json::to_value(result).unwrap();
    assert_eq!(wire["batch"]["requirements"], serde_json::json!([]));
}
