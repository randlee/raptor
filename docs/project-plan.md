# Raptor project plan

Phase A establishes Raptor's canonical models and JSON Schema, the SQLite reference
store, the plugin foundation, operational import/validation, and deterministic
rendering and round trips. The authoritative scope, sequencing, acceptance criteria,
and sprint links are maintained in [the Phase A plan](plans/phase-a/plan-phase-a.md).

Sprint-specific implementation decisions remain in the linked plans under
`docs/plans/phase-a/`; this file is only the stable project-level entry point.

Phase A remains open through A9–A12. A9 and A10 establish configured ingress
and SQLite export; A11 ports the reference extractor and safely updates the
canonical/storage contract; A12 performs the external-corpus round-trip proof
defined in
[the Phase A round-trip completion requirements](requirements-migration.md).
