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
