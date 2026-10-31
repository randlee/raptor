use crate::{
    error::RecordPosition,
    schema::{Decision, Requirement},
};
use serde::{Serialize, Serializer};

#[derive(Debug)]
struct PositionedRow<T> {
    position: RecordPosition,
    value: T,
}

/// Records admitted by `accept`; batches cannot be constructed by callers.
///
/// ```compile_fail
/// let _batch = raptor_schema::Batch::default();
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
    pub(crate) fn add_requirement(&mut self, position: usize, value: Requirement) {
        self.requirements.push(PositionedRow {
            position: RecordPosition(position),
            value,
        });
    }
    pub(crate) fn add_decision(&mut self, position: usize, value: Decision) {
        self.decisions.push(PositionedRow {
            position: RecordPosition(position),
            value,
        });
    }
    pub fn requirements(&self) -> impl Iterator<Item = (usize, &Requirement)> {
        self.requirements
            .iter()
            .map(|row| (row.position.0, &row.value))
    }
    pub fn decisions(&self) -> impl Iterator<Item = (usize, &Decision)> {
        self.decisions
            .iter()
            .map(|row| (row.position.0, &row.value))
    }
}
