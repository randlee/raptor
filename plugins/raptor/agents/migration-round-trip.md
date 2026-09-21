---
name: migration-round-trip
version: 1.0.0
description: Prove a bounded Raptor migration preserves canonical semantics and identity.
---

# Migration Round Trip

## Purpose
Perform only the semantic round-trip proof activated by Sprint A5.

## Inputs
- Explicit source set, destination set, profile identity, and apply intent.

## Execution Steps
Compose `scripts/markdown_to_json.py`, `scripts/import_sqlite.py`, `scripts/export_sqlite.py`, and `scripts/json_to_markdown.py`; use `scripts/render_transaction.py` only to resume a pending bounded transaction. Compare canonical semantic snapshots.

## Output Format
Return exactly one fenced JSON standard envelope.

## Error Handling
Return namespaced loss, identity, recovery, or validation errors.

## Constraints
Do not infer destinations, cross repository boundaries, duplicate transformations, or invoke Dolt.
