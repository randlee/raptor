use raptor_schema::Error;
use serde_json::{Value, json};

pub(super) fn fixture() -> Value {
    let records = r#"{
      "requirements": [{
        "id": "REQ-FIX-0001", "title": "Persist records", "status": "Active",
        "version": "1.0.0", "created": "2000-02-29", "last_updated": "2026-01-01",
        "owner": "Example", "supersedes": null, "superseded_by": null,
        "requirement_statement": {"text": "Persist", "statements": [
          {"modal": "Must", "text": "Keep records"}]},
        "rationale": "Preserve information",
        "success_criteria": {"text": "Verified", "acceptance_criteria": [
          {"text": "Read back", "checked": null}], "test_evidence": []},
        "dependencies": {"text": "", "requires": [], "related": []},
        "product_applicability": {"text": "", "applies_to": [], "does_not_apply_to": []},
        "implementation_notes": {"text": "", "key_considerations": []},
        "test_strategy": {"text": "", "test_types": []},
        "related_documents": {"text": "", "requirements": [], "architecture_decisions": [],
          "design_documents": [], "work_items": [], "external_references": []}
      }],
      "decisions": [{
        "id": "ADR-FIX-0001", "title": "Storage", "status": "Approved",
        "version": "1.0.0", "created": "2000-02-29", "last_updated": "2026-01-01",
        "owner": "Example", "supersedes": null, "superseded_by": null,
        "decision_date": "2026-01-01",
        "context": {"text": "Need storage", "background": "", "problem_statement": ""},
        "decision": {"text": "Use a database", "chosen_approach": "", "key_principles": []},
        "rationale": {"text": "Durability", "benefits": [], "trade_offs": []},
        "consequences": {"text": "", "positive": [], "negative": [], "neutral": []},
        "alternatives": {"text": "", "groups": []},
        "implementation": {"text": "", "key_components": [], "integration_points": [],
          "code_examples": ""},
        "impact_analysis": {"text": "", "affected_components": "", "performance_impact": "",
          "security_impact": "", "maintainability_impact": ""},
        "related_documents": {"text": "", "requirements": [], "architecture_decisions": [],
          "design_documents": [], "work_items": [], "external_references": []}
      }]
    }"#;
    serde_json::from_str(records).unwrap()
}
pub(super) fn check_error(
    error: &Error,
    category: &str,
    table: Option<&str>,
    position: Option<usize>,
    path: &str,
    item: Option<usize>,
    value: &Value,
) {
    assert_eq!(json!(error.category), category);
    assert_eq!(serde_json::to_value(error.table).unwrap(), json!(table));
    assert_eq!(error.record_position.map(|position| position.0), position);
    assert_eq!(error.field_path.as_ref(), path);
    assert_eq!(error.item_index().map(|index| index.0), item);
    assert_eq!(error.offending_value.as_ref(), value);
    assert!(!error.cause.is_empty());
    assert!(!error.message.is_empty());
    assert!(!error.recovery.is_empty());
    assert_ne!(error.recovery, error.cause.as_ref());
    assert_ne!(error.recovery, error.message.as_ref());
}
