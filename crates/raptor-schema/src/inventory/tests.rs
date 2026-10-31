use super::*;

#[derive(serde::Deserialize)]
struct Fixture {
    requirements: Vec<Requirement>,
    decisions: Vec<Decision>,
}

#[test]
fn defensive_inventory_check_reports_every_internal_duplicate()
-> Result<(), Box<dyn std::error::Error>> {
    let source = include_str!("../../../../tests/fixtures/records.json");
    let fixture: Fixture = serde_json::from_str(source)?;
    let duplicate_fixture: Fixture = serde_json::from_str(source)?;
    let mut requirements = fixture.requirements.into_iter();
    let first = requirements.next().ok_or("missing first requirement")?;
    let neighbor = requirements.next().ok_or("missing unique requirement")?;
    let duplicate = duplicate_fixture
        .requirements
        .into_iter()
        .next()
        .ok_or("missing duplicate fixture")?;

    // Only crate-internal construction can create this defensive-check input;
    // public accept rejects both occurrences before either enters its batch.
    let mut batch = Batch::new();
    batch.add_requirement(RecordPosition(1), first)?;
    batch.add_requirement(RecordPosition(2), neighbor)?;
    batch.add_requirement(RecordPosition(3), duplicate)?;
    for (position, row) in fixture.decisions.into_iter().enumerate() {
        batch.add_decision(RecordPosition(position), row)?;
    }

    let errors = check_inventory(&batch);
    assert_eq!(errors.len(), 2);
    for (error, position) in errors.iter().zip([1, 3]) {
        assert_eq!(error.category, ErrorCategory::DuplicateId);
        assert_eq!(error.table, Some(TableId::Req));
        assert_eq!(error.record_position, Some(RecordPosition(position)));
        assert_eq!(
            error.first_occurrence_record_position(),
            Some(RecordPosition(1))
        );
        assert_eq!(error.field_path.as_ref(), "/id");
        assert_eq!(error.offending_value.as_str(), Some("REQ-FIX-0001"));
        assert!(error.cause.contains("a unique identifier"));
        assert!(error.cause.contains("record position 1"));
    }
    Ok(())
}
