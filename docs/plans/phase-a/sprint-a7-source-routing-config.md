# Sprint A7 — Source routing configuration

## Objective

Define the Raptor-owned contract that binds every authorized scan source to one
exact source profile and a non-empty allowlist of canonical artifact families.

## Deliverables

| ID | Deliverable |
|---|---|
| A7-D1 | Public Pydantic models for `.raptor/routing.toml`. |
| A7-D2 | Generated `repository-routing-config.schema.json`. |
| A7-D3 | Cross-file validation between scan sources and routes. |
| A7-D4 | Normative routing field and failure requirements with neutral examples. |
| A7-D5 | Updated deterministic plugin vendor containing the routing contract. |

## Acceptance criteria

| ID | Criterion |
|---|---|
| A7-AC1 | Every configured scan source has exactly one route and no route references an undeclared source. |
| A7-AC2 | Every route selects one exact profile ID/version and at least one unique canonical artifact family. |
| A7-AC3 | Missing, unknown, duplicate, empty, floating, and unsupported routing values fail closed. |
| A7-AC4 | Resolved route order follows scan-source declaration order, independent of routing declaration order. |
| A7-AC5 | JSON Schema enforces every expressible structural constraint; cross-file source coverage is explicitly documented as runtime validation. |
| A7-AC6 | Examples and tests use only Raptor-owned identifiers and neutral repository categories. |
| A7-AC7 | Schema, plugin, typing, drift, neutrality, and independent QA gates pass. |

## Deferred configuration

- lifecycle and status mappings;
- Markdown section and field aliases;
- typed measurement mappings;
- identifier namespaces and extraction rules;
- template-set and materialization output selection;
- profile installation and executable loading policy.
