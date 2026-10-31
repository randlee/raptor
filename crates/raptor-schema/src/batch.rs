use crate::{
    error::{Error, RecordPosition, TableId},
    schema::{Decision, Requirement, validate_table_id},
};
use serde::{Serialize, Serializer};

#[derive(Debug)]
struct PositionedRow<T> {
    position: RecordPosition,
    value: T,
}

/// A position and the accepted record stored at that position.
#[derive(Debug)]
pub struct RowRef<'a, T> {
    pub position: RecordPosition,
    pub value: &'a T,
}

/// Records admitted by `accept`; batches cannot be constructed by callers.
///
/// ```compile_fail
/// let _batch = raptor_schema::Batch::default();
/// ```
///
/// ```compile_fail
/// let _batch = raptor_schema::Batch::new();
/// ```
///
/// ```compile_fail
/// fn mutate(batch: &mut raptor_schema::Batch, row: raptor_schema::Requirement) {
///     batch.add_requirement(raptor_schema::RecordPosition(0), row);
/// }
/// ```
///
/// ```compile_fail
/// fn mutate(batch: &mut raptor_schema::Batch, row: raptor_schema::Decision) {
///     batch.add_decision(raptor_schema::RecordPosition(0), row);
/// }
/// ```
#[derive(Debug, Serialize)]
pub struct Batch {
    #[serde(serialize_with = "unpositioned")]
    requirements: Vec<PositionedRow<Requirement>>,
    #[serde(serialize_with = "unpositioned")]
    decisions: Vec<PositionedRow<Decision>>,
}
fn unpositioned<T: Serialize, S: Serializer>(
    rows: &[PositionedRow<T>],
    serializer: S,
) -> Result<S::Ok, S::Error> {
    serializer.collect_seq(rows.iter().map(|row| &row.value))
}
impl Batch {
    pub(crate) fn new() -> Self {
        Self {
            requirements: Vec::new(),
            decisions: Vec::new(),
        }
    }
    pub(crate) fn add_requirement(
        &mut self,
        position: RecordPosition,
        value: Requirement,
    ) -> Result<(), Error> {
        validate_table_id(TableId::Req, &value.identity.id).map_err(|mut error| {
            error.table = Some(TableId::Req);
            error.record_position = Some(position);
            error
        })?;
        self.requirements.push(PositionedRow { position, value });
        Ok(())
    }
    pub(crate) fn add_decision(
        &mut self,
        position: RecordPosition,
        value: Decision,
    ) -> Result<(), Error> {
        validate_table_id(TableId::Dec, &value.identity.id).map_err(|mut error| {
            error.table = Some(TableId::Dec);
            error.record_position = Some(position);
            error
        })?;
        self.decisions.push(PositionedRow { position, value });
        Ok(())
    }
    pub fn requirements(&self) -> impl Iterator<Item = RowRef<'_, Requirement>> {
        self.requirements.iter().map(|row| RowRef {
            position: row.position,
            value: &row.value,
        })
    }
    pub fn decisions(&self) -> impl Iterator<Item = RowRef<'_, Decision>> {
        self.decisions.iter().map(|row| RowRef {
            position: row.position,
            value: &row.value,
        })
    }
}

#[cfg(test)]
mod tests;
