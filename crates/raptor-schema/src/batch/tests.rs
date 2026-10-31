use super::*;
use crate::{error::ErrorCategory, schema::Id};
use serde::Deserialize;

#[derive(Deserialize)]
struct Fixture {
    requirements: Vec<Requirement>,
    decisions: Vec<Decision>,
}

#[test]
fn insertion_guards_reject_wrong_kinds_without_panicking() -> Result<(), Box<dyn std::error::Error>>
{
    let mut fixture: Fixture =
        serde_json::from_str(include_str!("../../../../tests/fixtures/records.json"))?;
    let mut requirement = fixture.requirements.pop().ok_or("missing requirement")?;
    let mut decision = fixture.decisions.pop().ok_or("missing decision")?;
    requirement.identity.id = Id::try_from("ADR-FIX-9999".to_owned())?;
    decision.identity.id = Id::try_from("REQ-FIX-9999".to_owned())?;
    let mut batch = Batch::new();
    let req_error = batch
        .add_requirement(RecordPosition(2), requirement)
        .err()
        .ok_or("guard admitted requirement")?;
    let dec_error = batch
        .add_decision(RecordPosition(3), decision)
        .err()
        .ok_or("guard admitted decision")?;
    assert_eq!(
        (
            req_error.category,
            req_error.table,
            req_error.record_position
        ),
        (
            ErrorCategory::InvalidId,
            Some(TableId::Req),
            Some(RecordPosition(2))
        )
    );
    assert_eq!(
        (
            dec_error.category,
            dec_error.table,
            dec_error.record_position
        ),
        (
            ErrorCategory::InvalidId,
            Some(TableId::Dec),
            Some(RecordPosition(3))
        )
    );
    assert_eq!(req_error.field_path.as_ref(), "/id");
    assert_eq!(dec_error.field_path.as_ref(), "/id");
    assert_eq!(batch.requirements().count(), 0);
    assert_eq!(batch.decisions().count(), 0);
    Ok(())
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

    let errors = crate::inventory::check_inventory(&batch);
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
