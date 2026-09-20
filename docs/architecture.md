# Architecture

Raptor's canonical contract is deliberately narrower than any source repository's
Markdown dialect. The executable boundary is the installable `schema/` package;
generated schemas are derived evidence, and source profiles are integration
ports. Persistence and rendering consume this contract but do not redefine it.

## Architectural Boundary Rules

> **Note:** `.claude/agents/arch-qa.md` enforces the rules defined in this section on every sprint QA run.
> RULE-001 and RULE-002 in that agent must be updated to match what is defined here.

### RULE-001: Canonical models remain consumer-neutral

Code under `schema/src/raptor_schema` may not import a consumer adapter, Markdown
parser, database driver, plugin runtime, or template engine. Consumer conventions
enter only through the `SourceProfile` protocol and namespaced extensions.

### RULE-002: Pydantic models are the schema authority

Files under `schema/json/` are generated from Pydantic models, never edited as an
independent contract. CI must regenerate them and reject drift.

### RULE-003: Identity is explicit and composite

Repository identity comes only from `.raptor/identity.json`. Document and artifact
keys are repository-scoped; no path, remote, directory name, hash, or local ID is
an implicit global identity.

### RULE-004: Resolution scope is caller-selected

Reference validation must use one explicit mode (`structural`, `document`,
`batch`, or `store`). It may not query ambient state. Store resolution requires an
explicit resolver.

### RULE-005: Integration code stays at integration boundaries

The later integration runtime must make source-profile loading deterministic,
offline, hash-verified, and opt-in for external code. A1 defines only the profile
protocol and boundary data. Discovery, loading, persistence, plugins, parsing,
and rendering live outside the canonical model package and are delivered only by
their owning sprints.

## Accepted decisions

The enforceable rationale for these rules is recorded in
[`docs/adr/`](adr/README.md): `ADR-RAP-001` through `ADR-RAP-005` are accepted.
