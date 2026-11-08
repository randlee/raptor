use super::*;

fn found(label: Modal, text: &str) -> Option<(&'static str, usize, usize)> {
    modal_mismatch(label, text).map(|mismatch| (mismatch.found, mismatch.offset, mismatch.length))
}

#[test]
fn matching_keyword_or_no_keyword_is_not_reported() {
    assert_eq!(
        modal_mismatch(Modal::Must, "The cache MUST persist records."),
        None
    );
    assert_eq!(
        modal_mismatch(Modal::Should, "Logs SHOULD be rotated."),
        None
    );
    assert_eq!(
        modal_mismatch(Modal::MustNot, "Callers MUST NOT block."),
        None
    );
    assert_eq!(modal_mismatch(Modal::Must, "persist records"), None);
    assert_eq!(modal_mismatch(Modal::Must, ""), None);
}

#[test]
fn must_not_is_found_before_must() {
    assert_eq!(
        modal_mismatch(Modal::Must, "Startup MUST NOT fail on bad config."),
        Some(ModalMismatch {
            expected: "MUST",
            found: "MUST NOT",
            offset: 8,
            length: 8,
        })
    );
    assert_eq!(
        found(Modal::MustNot, "Startup MUST fail fast."),
        Some(("MUST", 8, 4))
    );
}

#[test]
fn keywords_without_a_modal_always_mismatch() {
    for (text, keyword) in [
        ("The tool SHALL log.", "SHALL"),
        ("The tool SHALL NOT log.", "SHALL NOT"),
        ("The tool MAY log.", "MAY"),
        ("Logging is REQUIRED.", "REQUIRED"),
        ("Logging is RECOMMENDED.", "RECOMMENDED"),
        ("Logging is NOT RECOMMENDED.", "NOT RECOMMENDED"),
        ("Logging is OPTIONAL.", "OPTIONAL"),
        ("The tool SHOULD NOT log.", "SHOULD NOT"),
    ] {
        for label in [Modal::Must, Modal::Should, Modal::MustNot] {
            assert_eq!(
                modal_mismatch(label, text).map(|mismatch| mismatch.found),
                Some(keyword),
                "{text} under {label:?}"
            );
        }
    }
}

#[test]
fn only_uppercase_whole_words_count() {
    for text in [
        "The tool must log.",
        "Must log.",
        "MUSTARD is MAYHEM; SHOULDER the OPTIONALS",
        "MUST_NOT_FAIL is a constant",
        "X_MUST is a constant",
        "MUST1 and 2MUST",
    ] {
        assert_eq!(modal_mismatch(Modal::Should, text), None, "{text}");
    }
}

#[test]
fn first_keyword_decides_and_offsets_count_characters() {
    assert_eq!(
        found(
            Modal::Must,
            "`reloadOnChange` MAY be enabled; otherwise MUST bind once."
        ),
        Some(("MAY", 17, 3))
    );
    assert_eq!(found(Modal::Must, "X MUST do A and MUST NOT do B."), None);
    assert_eq!(
        found(Modal::Must, "Café — MUST NOT drop"),
        Some(("MUST NOT", 7, 8))
    );
    assert_eq!(
        found(Modal::Must, "MUST\n  NOT drop"),
        Some(("MUST NOT", 0, 10))
    );
    assert_eq!(found(Modal::Must, "MUSTNOT drop"), None);
}

#[test]
fn modal_keywords_are_the_catalog_label_spellings() {
    let labelled: Vec<_> = crate::fields::FIELDS
        .iter()
        .filter_map(|field| match field.shape {
            crate::metadata::Shape::Statements(modal) => Some((modal, field.label)),
            _ => None,
        })
        .collect();
    assert_eq!(labelled.len(), 3);
    for (modal, label) in labelled {
        assert_eq!(label, format!("{} statements", modal.keyword()));
        assert_eq!(
            KEYWORDS
                .iter()
                .find(|(_, named)| *named == Some(modal))
                .map(|(k, _)| *k),
            Some(modal.keyword())
        );
    }
}
