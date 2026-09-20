# Sprint A4 — sc-compose Rendering and Semantic Round Trip

## Objective

Add sc-compose templates for every canonical family, expose JSON-to-Markdown rendering through the shared plugin, and prove that render/reparse preserves canonical meaning and source lineage.

- Branch: `phase-a/04-render-and-roundtrip`
- Stack relation: `must_follow A3`
- Merge-forward trigger: A3 development is pushed; merge A3 into A4 before every development/fix round.
- PR-completion trigger: A3 PR merges first.

## Scope boundary

Templates under `plugins/raptor/templates/` accept only A1-valid canonical JSON projected through the source-profile contract. The sprint adds shared `scripts/json_to_markdown.py` and semantic comparison support beside the A3 scripts, changes the export router's `json-md` route from unsupported to supported, and makes `/raptor:round-trip` compose import, validate, export, and comparison operations. No transformation logic moves into router skills. No external repository template, fixture, or compatibility suite is imported.

Normative design reference: [`references/claude-code-skills-agents-guidelines-v0.7.md`](references/claude-code-skills-agents-guidelines-v0.7.md). This committed copy is the sole contract. A4 preserves A3's thin-skill/focused-agent, versioned-frontmatter, registry, fenced-envelope, namespaced-error, progressive-disclosure, repo-root allowlist, dry-run/apply, atomic-write, redaction, and dual-client inventory contracts.

A4 adds exactly two focused agents:

```text
plugins/raptor/agents/
  json-markdown-export.md
  migration-round-trip.md
```

`agents/registry.yaml` registers both with exact paths/versions and adds compatible constraints for the export and round-trip skills. `json-markdown-export` renders one validated JSON document. `migration-round-trip` coordinates semantic proof by invoking the existing import, validate, and export routes; it does not contain their format logic. There is no monolithic multi-format execution agent.

For the `json-md` export route and `/raptor:round-trip`, verifying `sc-compose` presence and minimum version is the first executable step, before agent delegation. Failure halts with guidance from the respective `references/installation-and-troubleshooting.md`; no degraded renderer is allowed.

## Render and comparison contract

```python
def render_markdown(
    document: SourceDocument,
    *,
    profile: SourceProfile,
    template_set: str,
) -> RenderedDocument: ...

def compare_semantics(
    expected: SourceDocument,
    actual: SourceDocument,
    *,
    profile: SourceProfile,
) -> SemanticComparison: ...
```

`SemanticComparison` reports missing, added, and changed canonical paths. Normalization excludes only A1-documented presentation fields and transport-derived values such as a newly rendered byte hash. It separately verifies repository-relative source identity, parser profile, artifact IDs, and source-to-artifact membership.

The existing stable public commands gain these supported routes:

```text
/raptor:export json-md --profile <profile> --template-set <set> --input <json> --output <path>
/raptor:round-trip --profile <profile> --template-set <set> --input <markdown-or-json>
```

## Authoritative deliverables

| ID | Deliverable | Expected evidence |
|---|---|---|
| A4-D1 | Shared sc-compose template set with explicit entry templates for Requirement, NonFunctionalRequirement, ArchitectureDecision, DesignDocument, and TestPlan plus macros/partials. | all `.j2` files under `plugins/raptor/templates/` |
| A4-D2 | Model-to-template projection and strict pre-render validation rejecting missing/unsupported family data before output. | projection API and negative tests |
| A4-D3 | Shared `scripts/json_to_markdown.py` and semantic comparison implementation with atomic output, stable diagnostics, and documented template selection. | shared scripts and tests |
| A4-D4 | Semantic normalizer/comparator with path-level loss reporting and explicit presentation/transport-derived field treatment. | public API and unit tests |
| A4-D5 | Operational `/raptor:round-trip` router composing the other three skills for every family: Markdown -> validation -> JSON -> SQLite -> JSON -> sc-compose -> reparse -> semantic comparison. | composition and five-family integration suite |
| A4-D6 | Template inventory/render-matrix audit proving every family, partial, and required data field is exercised and undefined variables fail. | automated audit gate |
| A4-D7 | External template-set guide explaining how consumers keep templates and fixtures in their own repositories while using Raptor projection/comparison contracts. | documentation |
| A4-D8 | Focused JSON→Markdown and migration-round-trip agents with versioned frontmatter and registry/skill constraints. | two agent files, registry update, invocation tests |
| A4-D9 | Complete dual-client package inventory covering all four skills, focused references, eight agents, shared scripts, every `.j2` template/partial, vendor, and manifest metadata. | manifest/inventory validation gate |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| A4-AC1 | Each family selects one explicit entry template, renders deterministic Markdown from the same input, and fails on undefined variables. |
| A4-AC2 | Every canonical field is classified as rendered, recoverable by documented profile rule, or explicitly non-semantic/transport-derived; none is unclassified. |
| A4-AC3 | `/raptor:export` routes `json-md` to the shared renderer, while `/raptor:round-trip` composes the other skills without duplicating their transformation logic. |
| A4-AC4 | Intentional omission or mutation of any canonical field returns a non-equal result naming the precise path. |
| A4-AC5 | Rendering is atomic: validation or template failure leaves no partial destination file. |
| A4-AC6 | Template inventory includes every required `.j2` entry/partial, and both client manifests continue resolving the exact four stable public command names. |
| A4-AC7 | All five end-to-end cases compare semantically equal after SQLite recovery, render, and reparse, including relationships, extensions, meaningful order, and lineage. |
| A4-AC8 | All examples originate from the Raptor corpus; no P3 asset, `NFT`, Dolt/MySQL implementation, Rust SQLx, or bulk migration is added. |
| A4-AC9 | Dolt references remain future-interface notes returning structured unsupported; A4 adds no Dolt DDL, driver, connection, fixture, or test. |
| A4-AC10 | A documented external template set renders through the public projection API without editing Raptor templates or comparator. |
| A4-AC11 | Export `json-md` and round-trip check `sc-compose` as their first executable step, enforce minimum version, and use installation/troubleshooting guidance on failure. |
| A4-AC12 | Both new agents have versioned frontmatter, registry path/version constraints, single responsibilities, and fenced standard JSON envelopes with namespaced errors. |
| A4-AC13 | Rendering/round-trip paths reject out-of-root paths, default mutations to validate/dry-run, require explicit apply, write atomically, and expose neither secrets nor tool traces. |
| A4-AC14 | CI fails for an omitted/unregistered agent, skill, script, focused reference, `.j2` entry/partial, vendor file, or client-manifest inventory mismatch. |

## Authoritative validation

```sh
python -m pip install -e 'schema[test]'
which sc-compose && sc-compose --version
python -m pytest plugins/raptor/tests/render plugins/raptor/tests/round_trip
python -m pytest plugins/raptor/tests/round_trip -k 'requirement or non_functional or architecture_decision or design_document or test_plan'
python plugins/raptor/scripts/validate_plugin.py --guideline docs/plans/phase-a/references/claude-code-skills-agents-guidelines-v0.7.md --check-frontmatter --check-registry --check-manifests --check-inventory --check-templates
mkdir -p plugins/raptor/tests/.tmp
sc-compose render --root plugins/raptor/templates --file requirement.md.j2 --var-file plugins/raptor/tests/fixtures/raptor/requirement.json --output plugins/raptor/tests/.tmp/REQ-RAP-rendered.md
python plugins/raptor/scripts/json_to_markdown.py --profile raptor --template-set raptor --input plugins/raptor/tests/fixtures/raptor/requirement.json --output plugins/raptor/tests/.tmp/REQ-RAP-script-rendered.md --validate
python plugins/raptor/scripts/json_to_markdown.py --profile raptor --template-set raptor --input plugins/raptor/tests/fixtures/raptor/requirement.json --output plugins/raptor/tests/.tmp/REQ-RAP-script-rendered.md --apply
find plugins/raptor/templates -name '*.j2' -print | sort
git diff --exit-code -- plugins/raptor/_vendor/raptor_schema plugins/raptor/plugin-manifest.json
test ! -e schema/sql/dolt
test ! -e plugins/raptor/tests/fixtures/dolt
rg --files plugins/raptor/tests | rg '(?i)(^|/)dolt([^/]*)(integration|fixture)|(^|/)(integration|fixture)[^/]*dolt' && exit 1 || true
rg -n '\b(doltpy|mysqlclient|pymysql|mysql-connector|sqlx)\b' schema/pyproject.toml Cargo.toml plugins/raptor/plugin-manifest.json && exit 1 || true
rg -n '^\s*(from|import)\s+(dolt|doltpy|mysql)|dolt://|mysql://' plugins/raptor/scripts schema/src && exit 1 || true
rg -n 'unsupported|RAPTOR\.UNSUPPORTED\.DOLT' plugins/raptor/skills/import/references/json-dolt.md plugins/raptor/skills/export/references/dolt-json.md plugins/raptor/skills/validate/references/dolt.md
rg -n '\bNFT\b|p3-documentation|REQ-P3-|NFR-P3-|ADR-P3-' plugins/raptor schema/tests && exit 1 || true
```

Tests own and clean repository-root `.tmp/` paths. Integration tests cover exact public command discovery, route composition, CLI preflight ordering/failure, registry mismatch, fenced envelopes, namespaced errors, path rejection, validate/apply behavior, atomic failure, redaction, and client inventory equality. Generated Markdown is test output unless a Raptor dogfood document is intentionally updated and reviewed.

## Traceability

| Deliverable | Phase requirements |
|---|---|
| A4-D1, A4-D2 | PA-REQ-007, PA-REQ-001, PA-NFR-004 |
| A4-D3, A4-D6 | PA-REQ-006, PA-NFR-006 |
| A4-D4, A4-D5 | PA-REQ-002, PA-REQ-005, PA-REQ-008, PA-NFR-004 |
| A4-D5, A4-D7 | PA-REQ-009, PA-NFR-001, PA-NFR-002 |
| A4-D8, A4-D9 | PA-REQ-006, PA-NFR-004, PA-NFR-006 |

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Templates silently drop fields | require field classification and mutation tests with path-level loss detection. |
| Presentation differences create false failures | normalize only A1-approved presentation/transport fields and test equal/unequal cases. |
| One template accumulates family branches | separate family entry templates; share macros only for common structures. |
| External formatting needs leak into built-ins | expose consumer-owned template sets through projection; add no consumer conditionals. |
| A4 model changes bypass the plugin vendor | require the A3 refresh/check contract and clean manifest/hash diff in A4 CI. |
| Round-trip becomes a fifth implementation path | router composes import, validate, and export skills; only comparison logic is new shared code. |
| sc-compose is absent or shadowed on agent PATH | require first-step version/fallback checks and installation/troubleshooting reference before delegation. |
| A client package omits an agent or Jinja template | compare filesystem, registry, plugin manifest, and both client package inventories in CI. |
| Rendering leaks traces or writes outside scope | enforce fenced envelopes/redaction, repo-root allowlists, validate-by-default, explicit apply, and atomic output. |

## Non-closure

- No byte-for-byte Markdown preservation guarantee.
- No external repository template, fixture, migration, or compatibility suite.
- No in-place bulk rewrite of Raptor or consumer documentation.
- No Dolt/MySQL, Rust SQLx, web UI, or fleet orchestration.

## Phase handoff

Phase A closes when A1–A4 acceptance criteria pass and the Raptor-owned pipeline has evidence. A later phase may add `schema/sql/dolt/`, a Dolt adapter, and run the same persistence conformance suite before consumer-owned pilots. It must not weaken semantic comparison or move consumer rules into canonical models.
