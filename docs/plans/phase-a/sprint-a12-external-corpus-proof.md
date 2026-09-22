# Sprint A12 — External Corpus Proof

## Objective

Run the completed Raptor loop in the consumer checkout and prove that direct
extraction, SQLite storage, sc-compose rendering, and the consumer validator
preserve the authorized documentation.

- Branch: `phase-a/12-external-corpus-proof`
- Stack relation: `must_follow A11`
- PR-completion trigger: A11 merges first.

Raptor stores no consumer source, configuration, templates, fixtures, or
runbook. The consumer agent retains commands and detailed reports locally.

## Deliverables

| ID | Deliverable | Evidence |
|---|---|---|
| A12-D1 | Create consumer-owned configuration and registered document identities using A9 operations. | Configuration validation and identity output stay in the consumer checkout. |
| A12-D2 | Run Raptor `markdown_to_json.py` over consumer roots and diff JSON field-by-field against `requirements-index.json`. | 784/784 records, zero blocked, and a plain comparison report. |
| A12-D3 | Run JSON→SQLite→JSON→sc-compose→Markdown→JSON and the five-template parity diff. | Zero-loss round trip; rendered Markdown equals its source after LF normalization and one trailing newline. |
| A12-D4 | Run the consumer validator and declared secondary gates on Raptor-rendered Markdown. | Clean validator/gate result; counts reported to ATM. |

## Acceptance criteria

| ID | Criterion |
|---|---|
| A12-AC1 | Direct extraction is field-equal to the index for 784/784 records with zero blocked documents. |
| A12-AC2 | Every selected document completes the import, export, render, and reparse loop or has an explicit diagnostic. |
| A12-AC3 | Completed documents have zero loss for fields, ordering, relationships, identity, origin, and materialization provenance. |
| A12-AC4 | `render(extract(document))` is byte-equal to its source after LF normalization and one trailing newline. |
| A12-AC5 | The consumer validator and declared secondary gates are clean on rendered output. |
| A12-AC6 | Consumer source assets remain outside Raptor; ATM receives counts only. |

## Consumer commands

```sh
python3 plugins/raptor/scripts/markdown_to_json.py --repo-root <consumer-root> --config <consumer-config> --report <report> --apply
python3 plugins/raptor/scripts/import_sqlite.py --input <json> --database <sqlite> --apply
python3 plugins/raptor/scripts/export_sqlite.py --database <sqlite> --output <json>
python3 plugins/raptor/scripts/json_to_markdown.py --input <json> --output <markdown> --database <sqlite> --apply
# Run the consumer field-diff script, template parity diff, validator, and secondary gates.
```

## Traceability

| Requirement | A12 evidence |
|---|---|
| REQ-RAP-013, REQ-RAP-014 | Re-confirmed on the consumer corpus; owned by A9/A10. |
| REQ-RAP-015, REQ-RAP-016 | Field diff, SQLite round trip, template parity, and consumer gates. |
| NFR-RAP-008 | Explicit diagnostics and ATM count report. |

## Non-closure

A12 is a consumer-owned proof, not a consumer repository replacement, Rust
CLI, Dolt, SQLx, or fleet migration.
