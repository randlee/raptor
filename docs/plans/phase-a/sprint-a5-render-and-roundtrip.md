# Sprint A5 — sc-compose Rendering and Semantic Round Trip

## Objective

Activate JSON→Markdown and `/raptor:round-trip` with shared sc-compose templates for every canonical family, proving semantic preservation, composite identity stability, and the required origin/materialization provenance transition.

- Branch: `phase-a/05-render-and-roundtrip`
- Stack relation: `must_follow A4`
- Merge-forward trigger: A4 development is pushed; merge A4 into A5 before every development/fix round.
- PR-completion trigger: A4 PR merges first.

## Scope boundary

A5 adds `plugins/raptor/templates/`, shared `scripts/json_to_markdown.py` plus comparison support, activates `json-markdown-export` and `migration-round-trip`, changes `json-md`/round-trip from Phase-unsupported to supported, and preserves Dolt unsupported behavior. Skills remain routers; round-trip composes A4 routes rather than duplicating them.

Every authoritative deliverable must land production-ready. Templates, projection, rendering, provenance transitions, focused agents, route composition, and loss detection close together.

For JSON→Markdown and round-trip, checking `sc-compose` and its minimum version is the first executable step before agent delegation. Failure uses installation/troubleshooting guidance; no degraded renderer exists.

## Render/comparison contract

```python
def render_markdown(
    document: SourceDocument, *, profile: SourceProfile,
    template_set: str, output_path: RepositoryPath,
) -> RenderedDocument: ...

def compare_semantics(
    expected: SourceDocument, actual: SourceDocument, *, profile: SourceProfile,
) -> SemanticComparison: ...
```

Output path is required, repository-relative, resolved beneath repository root, and may equal the current path or be a new/moved path. Rendering never changes `OriginProvenance`. It creates rendered `MaterializationProvenance` with requested path, recomputed byte hash, prior materialization hash, current parse profile/version, and template set/version. Reparse must recover the serialized immutable origin; an attempted origin rewrite is `RAPTOR.PROVENANCE.ORIGIN_MUTATION`.

Every entry template emits a reserved, profile-defined machine-readable Raptor provenance block containing immutable origin and the non-self-referential materialization inputs needed for reparse. The output byte hash is computed only after atomic rendering and stored in the returned canonical object/database record; a template never embeds a hash of the bytes that contain that same hash.

Semantic comparison requires exact equality of composite repository/document/artifact keys, artifact family payloads, meaningful order, relationships, extensions, and immutable origin. It does not directly compare materialization path/hash/operation/template or transport locations; instead it validates A1's transition matrix, recomputes the output hash, verifies parent hash/path/template fields, and requires new locations to be valid for rendered bytes. Failures list missing/added/changed canonical paths and provenance transition violations.

## Template inventory

At minimum the manifest inventories these entry templates; every added macro/partial is also mandatory in both client packages and inventory gates:

```text
plugins/raptor/templates/
  requirement.md.j2
  non-functional-requirement.md.j2
  architecture-decision.md.j2
  design-document.md.j2
  test-plan.md.j2
```

## Authoritative deliverables

| ID | Deliverable | Expected evidence |
|---|---|---|
| A5-D1 | Five strict sc-compose entry templates plus inventoried shared macros/partials. | complete `plugins/raptor/templates/**/*.j2` inventory |
| A5-D2 | Model-to-template projection and pre-render validation rejecting missing/unsupported family data. | projection API and negative tests |
| A5-D3 | Atomic validate/apply JSON→Markdown shared implementation and focused export agent. | script/agent tests |
| A5-D4 | Path-level semantic comparator implementing A1 identity/origin/materialization equality and transition matrix. | public API and mutation tests |
| A5-D5 | Operational round-trip agent/router composing validate/import/export for all five families. | five-family integration suite |
| A5-D6 | Dual-client inventory gate covering all skills/references, eight agents, scripts, every `.j2`, vendor, registry, and manifest metadata. | CI/package audit |
| A5-D7 | External template-set guide retaining templates/fixtures in consumer repositories. | documentation and temporary external-template test |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| A5-AC1 | Each family selects one entry template, renders deterministically, fails undefined variables, and accounts for every canonical field. |
| A5-AC2 | JSON→Markdown defaults to validate, requires apply, rejects out-of-root/symlink escapes, and atomically writes no partial output. |
| A5-AC3 | Same-path and new-path render/reparse cases preserve immutable origin/composite keys and satisfy every materialization/hash/location transition rule. |
| A5-AC4 | All five pipelines Markdown→JSON→SQLite→JSON→Markdown→reparse compare semantically equal with identity-qualified evidence. |
| A5-AC5 | Mutation tests for payload, relationship repository namespace, origin, output hash, parent hash, template identity, and transport location produce exact path-level failures. |
| A5-AC6 | `/raptor:round-trip` composes existing routes through the shared runner; neither skill nor agent duplicates transformations. |
| A5-AC7 | `sc-compose` preflight precedes delegation and missing/old versions halt with troubleshooting guidance. |
| A5-AC8 | Both client packages contain the identical complete eight-agent and `.j2` inventory; omission/extra/hash/version drift fails CI. |
| A5-AC9 | Dolt references still return structured unsupported and no Dolt implementation is added. |
| A5-AC10 | No P3 asset, `NFT`, Rust SQLx, bulk rewrite/migration, secret, or raw tool trace is present. |

## Authoritative validation

```sh
python -m pip install -e 'schema[test]'
which sc-compose && sc-compose --version
python -m pytest plugins/raptor/tests/render plugins/raptor/tests/round_trip plugins/raptor/tests/provenance
python plugins/raptor/scripts/validate_plugin.py --guideline docs/plans/phase-a/references/claude-code-skills-agents-guidelines-v0.7.md --check-frontmatter --check-registry --check-manifests --check-inventory --check-vendor --check-templates
mkdir -p plugins/raptor/tests/.tmp
python plugins/raptor/scripts/json_to_markdown.py --repo-root . --profile raptor --template-set raptor --input plugins/raptor/tests/fixtures/raptor/requirement.json --output plugins/raptor/tests/.tmp/REQ-RAP-rendered.md --validate
python plugins/raptor/scripts/json_to_markdown.py --repo-root . --profile raptor --template-set raptor --input plugins/raptor/tests/fixtures/raptor/requirement.json --output plugins/raptor/tests/.tmp/REQ-RAP-rendered.md --apply
find plugins/raptor/templates -name '*.j2' -print | sort
git diff --exit-code -- plugins/raptor/_vendor/raptor_schema plugins/raptor/plugin-manifest.json
test ! -e schema/sql/dolt
test ! -e plugins/raptor/tests/fixtures/dolt
rg -n 'unsupported|RAPTOR\.UNSUPPORTED\.DOLT' plugins/raptor/skills/import/references/json-dolt.md plugins/raptor/skills/export/references/dolt-json.md plugins/raptor/skills/validate/references/dolt.md
```

Tests use and clean repository-root `.tmp/` paths.

## Traceability

| Deliverable | Phase requirements |
|---|---|
| A5-D1, A5-D2, A5-D3 | PA-REQ-007, PA-REQ-001, PA-NFR-004 |
| A5-D4, A5-D5 | PA-REQ-002, PA-REQ-005, PA-REQ-008, PA-NFR-004 |
| A5-D5, A5-D6 | PA-REQ-006, PA-NFR-006 |
| A5-D7 | PA-REQ-009, PA-NFR-001, PA-NFR-002 |

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Templates silently drop fields | field-accounting matrix and path-level mutation tests. |
| Provenance conflates immutable origin with output transport | separate models and explicit transition/equality matrix with recomputed hashes. |
| Round-trip becomes another implementation | compose A4 routes; only renderer/comparator logic is new shared code. |
| One client omits agent/template assets | compare filesystem, registry, manifest, and both package inventories. |

## Non-closure

- No byte-for-byte Markdown formatting preservation guarantee.
- No external repository template/fixture/migration/compatibility suite copied into Raptor.
- No in-place bulk rewrite of Raptor or consumer documentation.
- No Dolt/MySQL, Rust SQLx, web UI, or fleet orchestration.

## Phase handoff

Phase A closes when A1–A5 acceptance criteria pass. A later phase may add `schema/sql/dolt/` and a Dolt adapter running the same persistence conformance suite before consumer-owned pilots; it may not weaken composite identity, provenance, semantic comparison, or consumer-neutral boundaries.
