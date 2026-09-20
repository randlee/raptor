# Sprint A4 — Validate, Import, and Export Operations

## Objective

Activate the consumer-neutral Markdown/JSON/SQLite validation, import, and export routes on the A3 plugin foundation using shared scripts and six focused execution agents.

- Branch: `phase-a/04-plugin-operations`
- Stack relation: `must_follow A3`
- Merge-forward trigger: A3 development is pushed; merge A3 into A4 before every development/fix round.
- PR-completion trigger: A3 PR merges first.

## Scope boundary

A4 implements Markdown→JSON, JSON→SQLite, SQLite→JSON, and Markdown/JSON/SQLite validation. `/raptor:export json-md` and `/raptor:round-trip` continue returning `RAPTOR.UNSUPPORTED.PHASE` until A5. Dolt routes remain `RAPTOR.UNSUPPORTED.DOLT`. Public command names, router paths, registry policy, runner, client adapters, vendor/bootstrap, and response envelopes remain A3 contracts.

Every authoritative deliverable must land production-ready for the six supported routes. No router, agent, script, source-profile behavior, mutation guard, or diagnostic may be a shape-only placeholder.

## Supported route/agent/script matrix

| Public route | Focused agent | Shared implementation |
|---|---|---|
| `/raptor:import md-json` | `markdown-json-import` | `scripts/markdown_to_json.py` |
| `/raptor:import json-sqlite` | `json-sqlite-import` | `scripts/import_sqlite.py` |
| `/raptor:export sqlite-json` | `sqlite-json-export` | `scripts/export_sqlite.py` |
| `/raptor:validate markdown` | `markdown-validate` | `scripts/validate.py markdown` |
| `/raptor:validate json` | `json-validate` | `scripts/validate.py json` |
| `/raptor:validate sqlite` | `sqlite-validate` | `scripts/validate.py sqlite` |

Skills only select the focused reference and ask the A3 runner to invoke its registered agent. Agents perform one operation and delegate data behavior to shared scripts/vendored APIs. No layer duplicates Pydantic or SQL logic.

## Source-profile execution contract

A4 implements A1's `SourceInput`, `ParsedSection`, `ParsedDocument`, `ComparableDocument`, `ProfileDescriptor`, and `SourceProfile` types exactly. Inputs require repository root, stable repository/document identities, and repository-relative path. Resolution order, exact/`1.x` version selection, module hash/API/entrypoint checks, `--allow-profile-code`, no-network rule, root/symlink allowlist, trust/failure codes, and external consumer-owned `.raptor/profiles/` workflow are acceptance contracts, not examples.

Before Markdown validation/import, the operation resolves repository/document identity only through `<repo-root>/.raptor/identity.json`. A shared `scripts/identity.py register` command exposes `--validate` and `--apply`: validate reports the proposed binding and conflicts without mutation; apply atomically creates or extends the A1 manifest. A missing legacy manifest returns `RAPTOR.IDENTITY.MISSING` with this exact remediation path. Repeat import reuses the binding; clone/root changes do not affect it; repository/document/path conflicts use A1 codes. Neither profile nor command derives an ID from the input path.

The built-in Raptor profile is the only committed profile/fixture source. A temporary test creates an external profile under a temporary consumer repository, invokes it by descriptor/path with explicit trust, and proves no consumer file is copied into plugin or Raptor source.

## Mutation and response contract

- Every file/database path resolves under the supplied repository root; `-` is allowed only for stdout JSON. Escapes fail with `RAPTOR.PATH.OUTSIDE_ROOT`.
- File/database mutation defaults to `--validate`/`--dry-run`, requires `--apply`, stages files for atomic replace, and uses one SQLite transaction.
- Diagnostics carry composite document/artifact identity and current materialization path. Agents return exactly one fenced standard JSON envelope with namespaced error and no secret/tool trace.
- Markdown import establishes immutable origin plus imported materialization. SQLite export returns those values unchanged. JSON→SQLite uses composite repository/document/artifact keys and A2 replacement semantics.
- Reference modes are explicit at every route: single-file Markdown validation/import uses `document`; directory/multi-file validation/import uses `batch`; context-free JSON validation defaults to `structural` and accepts `--reference-mode structural|document|batch|store` (`store` requires `--database`); JSON→SQLite uses A2 batch/store overlay resolution. Missing targets use A1 diagnostics, including the selected mode and fully qualified source/target keys.

## Authoritative deliverables

| ID | Deliverable | Expected evidence |
|---|---|---|
| A4-D1 | Six shared scripts/operation modes activating the matrix without duplicated schema/storage logic. | `plugins/raptor/scripts/` and tests |
| A4-D2 | Six focused agents activated through the shared runner with fenced envelopes and namespaced errors. | agent/runner integration tests |
| A4-D3 | Concrete identity registration/resolution and source-profile discovery/loading/trust/version/path implementation plus built-in Raptor profile. | identity/profile implementation and tests |
| A4-D4 | Deterministic structured validation diagnostics for Markdown, canonical JSON, and SQLite. | positive/negative diagnostic suite |
| A4-D5 | Atomic validate/apply Markdown→JSON, JSON→SQLite, and SQLite→JSON flows preserving composite identity and provenance. | route integration/conformance tests |
| A4-D6 | Updated dual-client inventories and external-consumer guide without consumer assets. | manifest gate and docs |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| A4-AC1 | Both clients route each supported operation to exactly the declared focused agent/shared script through the A3 runner. |
| A4-AC2 | Markdown→JSON emits deterministic A1-valid canonical JSON for all five Raptor-owned families with composite identity and origin/materialization provenance. |
| A4-AC3 | JSON→SQLite and SQLite→JSON satisfy A2 conformance, multi-repository identity, replacement/reference, validate/apply, rollback, and exact recovery rules. |
| A4-AC4 | Validation returns deterministic identity-qualified diagnostics and rejects malformed source/model/storage without mutation. |
| A4-AC5 | Profile tests cover precedence, version/API/entrypoint/hash, trust, root/symlink escape, invalid return types, and temporary external consumer profile without copy. |
| A4-AC6 | Files and databases are atomically mutated only with apply; failures leave no partial destination or transaction. |
| A4-AC7 | A3 vendor hash/bootstrap/registry/runner/client parity gates continue passing after scripts are added. |
| A4-AC8 | JSON→Markdown, round-trip, and Dolt retain their exact structured unsupported responses; no templates or Dolt implementation appear. |
| A4-AC9 | No P3 asset, `NFT`, Rust SQLx, duplicated client logic, secret, or raw tool trace is present. |
| A4-AC10 | Identity CLI tests cover validate versus apply, first/repeat import, clone/root-path change, repository/document/path conflict or reuse, and legacy missing identity without inference. |
| A4-AC11 | Route tests prove document, batch, structural, and store-backed reference modes with same-document, cyclic batch, existing-store, and missing cross-repository cases and exact diagnostics. |

## Authoritative validation

```sh
python -m pip install -e 'schema[test]'
python -m pytest plugins/raptor/tests/operations plugins/raptor/tests/profiles
python plugins/raptor/scripts/validate_plugin.py --guideline docs/plans/phase-a/references/claude-code-skills-agents-guidelines-v0.7.md --check-frontmatter --check-registry --check-manifests --check-inventory --check-vendor
mkdir -p plugins/raptor/tests/.tmp
python plugins/raptor/scripts/identity.py register --repo-root . --repository-id urn:raptor:repo:raptor --document-id DOC-RAP-001 --path docs/requirements.md --validate
python plugins/raptor/scripts/identity.py register --repo-root . --repository-id urn:raptor:repo:raptor --document-id DOC-RAP-001 --path docs/requirements.md --apply
python plugins/raptor/scripts/validate.py markdown --profile raptor --repo-root . --input docs/requirements.md --reference-mode document --format json
python plugins/raptor/scripts/markdown_to_json.py --profile raptor --repo-root . --input docs/requirements.md --reference-mode document --output plugins/raptor/tests/.tmp/canonical.json --validate
python plugins/raptor/scripts/markdown_to_json.py --profile raptor --repo-root . --input docs/requirements.md --reference-mode document --output plugins/raptor/tests/.tmp/canonical.json --apply
python plugins/raptor/scripts/import_sqlite.py --repo-root . --database plugins/raptor/tests/.tmp/phase-a.sqlite --input plugins/raptor/tests/.tmp/canonical.json --validate
python plugins/raptor/scripts/import_sqlite.py --repo-root . --database plugins/raptor/tests/.tmp/phase-a.sqlite --input plugins/raptor/tests/.tmp/canonical.json --apply
python plugins/raptor/scripts/export_sqlite.py --repo-root . --database plugins/raptor/tests/.tmp/phase-a.sqlite --repository-id urn:raptor:repo:raptor --document-id DOC-RAP-001 --output plugins/raptor/tests/.tmp/export.json --validate
python plugins/raptor/scripts/export_sqlite.py --repo-root . --database plugins/raptor/tests/.tmp/phase-a.sqlite --repository-id urn:raptor:repo:raptor --document-id DOC-RAP-001 --output plugins/raptor/tests/.tmp/export.json --apply
python plugins/raptor/scripts/validate.py json --repo-root . --input plugins/raptor/tests/.tmp/export.json --reference-mode structural --format json
test ! -e plugins/raptor/templates
test ! -e schema/sql/dolt
rg -n 'unsupported|RAPTOR\.UNSUPPORTED\.DOLT' plugins/raptor/skills/import/references/json-dolt.md plugins/raptor/skills/export/references/dolt-json.md plugins/raptor/skills/validate/references/dolt.md
```

## Traceability

| Deliverable | Phase requirements |
|---|---|
| A4-D1, A4-D2, A4-D6 | PA-REQ-006, PA-NFR-006 |
| A4-D3, A4-D4 | PA-REQ-002, PA-REQ-004, PA-NFR-001, PA-NFR-004 |
| A4-D5 | PA-REQ-003, PA-REQ-005, PA-REQ-009, PA-NFR-005 |

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Route logic leaks into skills/agents | matrix and tests require shared scripts/vendored APIs; client inventory checks parity. |
| External profile is mistaken for sandboxed content | require explicit trust, local hash/path checks, and document arbitrary-code boundary. |
| Multi-repo identities collapse to paths/local IDs | all commands require repository/document keys and run cross-repository collision tests. |
| Mutations bypass validation | default dry-run, explicit apply, atomic files, SQLite transactions, failure injection. |

## Non-closure

- No JSON→Markdown, templates, or semantic round-trip; A5 owns them.
- No Dolt DDL, driver, connection, fixture, integration test, or placeholder directory.
- No consumer profile/fixture copied into Raptor.
- No marketplace publishing, telemetry, network registry, or fleet migration.

## Handoff to A5

A5 consumes the verified foundation and six implemented routes. It adds only shared sc-compose templates, JSON→Markdown, the remaining two focused agents, and composed semantic round-trip while preserving all public names, identities, provenance, runner, vendor, and safety contracts.
