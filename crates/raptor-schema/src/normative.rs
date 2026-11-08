//! Normative-keyword detection for statement lines filed under a modal label.
//!
//! The statement modal comes from its label. This module never changes that
//! modal; it only reports when the line's own RFC 2119 keyword disagrees with
//! it, so the source document can be corrected.
use crate::schema::Modal;
use serde::Serialize;

/// Uppercase RFC 2119 keywords and the modal each one names, if any.
///
/// Keywords without a modal (for example `SHALL` or `MAY`) never match a
/// label: Raptor does not reinterpret them as one of its modals. At one
/// position the first entry that matches wins, so each multi-word keyword
/// precedes its one-word prefix.
const KEYWORDS: [(&str, Option<Modal>); 11] = [
    ("MUST NOT", Some(Modal::MustNot)),
    ("MUST", Some(Modal::Must)),
    ("SHALL NOT", None),
    ("SHALL", None),
    ("SHOULD NOT", None),
    ("SHOULD", Some(Modal::Should)),
    ("NOT RECOMMENDED", None),
    ("RECOMMENDED", None),
    ("REQUIRED", None),
    ("MAY", None),
    ("OPTIONAL", None),
];

impl Modal {
    /// The RFC 2119 keyword that names this modal.
    pub const fn keyword(self) -> &'static str {
        match self {
            Self::Must => "MUST",
            Self::Should => "SHOULD",
            Self::MustNot => "MUST NOT",
        }
    }
}

/// A statement whose own normative keyword disagrees with its label's modal.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ModalMismatch {
    /// Keyword of the label's modal.
    pub expected: &'static str,
    /// Canonical spelling of the keyword found in the statement.
    pub found: &'static str,
    /// Character offset of the found keyword in the statement text.
    pub offset: usize,
    /// Character length of the found keyword as written (inner whitespace kept).
    pub length: usize,
}

fn word_byte(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || byte == b'_'
}

/// Match `keyword` at byte `start`, its words separated by any ASCII
/// whitespace run; return the end.
fn match_keyword(text: &str, start: usize, keyword: &str) -> Option<usize> {
    let bytes = text.as_bytes();
    let mut position = start;
    for (index, word) in keyword.split(' ').enumerate() {
        if index > 0 {
            let gap = bytes
                .get(position..)?
                .iter()
                .take_while(|byte| byte.is_ascii_whitespace())
                .count();
            if gap == 0 {
                return None;
            }
            position += gap;
        }
        if !bytes.get(position..)?.starts_with(word.as_bytes()) {
            return None;
        }
        position += word.len();
    }
    match bytes.get(position) {
        Some(byte) if word_byte(*byte) => None,
        _ => Some(position),
    }
}

/// The leftmost uppercase RFC 2119 keyword in `text`, as whole words.
/// Returns the byte range and the keyword's table entry.
fn first_keyword(text: &str) -> Option<(usize, usize, &'static str, Option<Modal>)> {
    let bytes = text.as_bytes();
    (0..bytes.len())
        .filter(|&start| start == 0 || !word_byte(bytes[start - 1]))
        .find_map(|start| {
            KEYWORDS.iter().find_map(|(keyword, modal)| {
                match_keyword(text, start, keyword).map(|end| (start, end, *keyword, *modal))
            })
        })
}

/// Report when the first normative keyword in a statement names a different
/// modal than its label. A statement without a keyword is never reported.
pub fn modal_mismatch(label: Modal, text: &str) -> Option<ModalMismatch> {
    let (start, end, found, modal) = first_keyword(text)?;
    if modal == Some(label) {
        return None;
    }
    Some(ModalMismatch {
        expected: label.keyword(),
        found,
        offset: text.get(..start)?.chars().count(),
        length: text.get(start..end)?.chars().count(),
    })
}

#[cfg(test)]
mod tests;
