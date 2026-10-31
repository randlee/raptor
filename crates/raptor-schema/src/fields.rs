mod decisions;
mod requirements;
use crate::metadata::Field;

/// Field catalog in canonical emission order.
pub(crate) static FIELDS: [Field; requirements::FIELDS.len() + decisions::FIELDS.len()] = {
    let mut fields =
        [requirements::FIELDS[0]; requirements::FIELDS.len() + decisions::FIELDS.len()];
    let mut index = 0;
    while index < requirements::FIELDS.len() {
        fields[index] = requirements::FIELDS[index];
        index += 1;
    }
    let mut decision = 0;
    while decision < decisions::FIELDS.len() {
        fields[index] = decisions::FIELDS[decision];
        index += 1;
        decision += 1;
    }
    fields
};
