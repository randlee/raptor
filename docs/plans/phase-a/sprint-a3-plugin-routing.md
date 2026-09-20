# Sprint A3 — Claude + Codex Operation Routing

## Objective

Package the Phase A schema contracts as a self-contained `raptor` plugin with stable import, export, validate, and round-trip command routers for Claude and Codex, backed by one shared Python implementation.

- Branch: `phase-a/03-plugin-routing`
- Stack relation: `must_follow A2`
- Merge-forward trigger: A2 development is pushed; merge A2 into A3 before every development/fix round.
- PR-completion trigger: A2 PR merges first.

## Scope boundary

A3 establishes every public router and implements the Phase A ingest/storage paths: Markdown→JSON, JSON→SQLite, SQLite→JSON, and validation of Markdown, JSON, and SQLite. JSON→Markdown and operational semantic round-trip remain explicitly unsupported until A4. Dolt routes are future-interface notes that return structured unsupported results throughout Phase A; they add no DDL, driver, connection, fixture, or integration test.

External consumers own and test their source profiles in their repositories. Raptor ships only its dogfood profile and consumer-neutral routing boundaries.

Normative design reference: [`references/claude-code-skills-agents-guidelines-v0.7.md`](references/claude-code-skills-agents-guidelines-v0.7.md). Its provenance header records the sibling source and commit, but the committed copy is the sole normative contract; implementation and CI must not read the sibling checkout.

## Stable public surface and layout

The plugin namespace and command names are stable API:

```text
/raptor:import
/raptor:export
/raptor:validate
/raptor:round-trip
```

Both discovery systems must resolve those exact names to the matching skill directories:

```text
plugins/raptor/
  .claude-plugin/plugin.json
  .codex-plugin/plugin.json
  plugin-manifest.json
  skills/
    import/
      SKILL.md
      references/installation-and-troubleshooting.md
      references/md-json.md
      references/json-sqlite.md
      references/json-dolt.md
    export/
      SKILL.md
      references/installation-and-troubleshooting.md
      references/sqlite-json.md
      references/json-md.md
      references/dolt-json.md
    validate/
      SKILL.md
      references/installation-and-troubleshooting.md
      references/markdown.md
      references/json.md
      references/sqlite.md
      references/dolt.md
    round-trip/
      SKILL.md
      references/installation-and-troubleshooting.md
  agents/
    registry.yaml
    markdown-json-import.md
    json-sqlite-import.md
    sqlite-json-export.md
    markdown-validate.md
    json-validate.md
    sqlite-validate.md
  scripts/
    validate.py
    markdown_to_json.py
    import_sqlite.py
    export_sqlite.py
    validate_plugin.py
  _vendor/raptor_schema/
  tests/
```

Skills are thin discovery/router layers using progressive disclosure; `SKILL.md` loads only the selected focused reference and agent contract. They do not implement transformations. Every skill and agent has versioned YAML frontmatter. `agents/registry.yaml` pins agent-relative paths/versions and each skill's compatible agent constraints; resolution fails closed on missing or mismatched entries. The public command names are an intentional user-required exception to the guideline's gerund naming preference.

Each implemented operation has one focused execution agent; no agent branches across formats. Agents return fenced JSON only, using the standard `success`, `canceled`, `aborted_by`, `data`, `error`, and `metadata` envelope. Error objects use namespaced codes such as `RAPTOR.VALIDATION.INPUT`, `RAPTOR.PATH.OUTSIDE_ROOT`, and `RAPTOR.UNSUPPORTED.DOLT`, with `message`, `recoverable`, and `suggested_action`. Skills reject malformed or unfenced agent responses and never surface tool traces or secrets.

Shared Python logic exists only in `plugins/raptor/scripts/`. Inputs and outputs are restricted to a resolved repository-root allowlist; stdout (`-`) is the only non-file output exception. Mutating operations default to `--validate`/`--dry-run`, require explicit apply intent, use atomic replacement, and leave no partial file/database state. Every skill checks required external CLIs and minimum versions as its first executable step before agent delegation and routes missing tools to its `references/installation-and-troubleshooting.md`.

The generated `_vendor/raptor_schema/` is copied from authoritative `schema/src/raptor_schema/`, never hand-edited. `plugin-manifest.json` records canonical schema version and deterministic source-content hash plus packaged skill, agent, script, and template inventory. One documented refresh operation removes stale vendor files, copies source, updates metadata, and offers CI check mode.

## Route support matrix

| Public command | Reference/route | A3 behavior |
|---|---|---|
| `/raptor:import` | `md-json` | supported through shared Markdown-to-JSON script and selected source profile |
| `/raptor:import` | `json-sqlite` | supported through shared SQLite import script |
| `/raptor:import` | `json-dolt` | structured `unsupported` result with later-phase boundary |
| `/raptor:export` | `sqlite-json` | supported through shared SQLite export script |
| `/raptor:export` | `json-md` | structured `unsupported` result naming A4 ownership |
| `/raptor:export` | `dolt-json` | structured `unsupported` result with later-phase boundary |
| `/raptor:validate` | `markdown`, `json`, `sqlite` | supported through shared validation script/APIs |
| `/raptor:validate` | `dolt` | structured `unsupported` result with later-phase boundary |
| `/raptor:round-trip` | semantic migration | structured `unsupported` result naming A4 ownership |

Unsupported results have a stable machine-readable code, requested operation, phase/status, and remediation/availability message; unsupported is never reported as success.

## Authoritative deliverables

| ID | Deliverable | Expected evidence |
|---|---|---|
| A3-D1 | Plugin foundation with both manifests resolving the exact four `raptor` public command names to their router skills. | `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, discovery tests |
| A3-D2 | Import, export, validate, and round-trip router skills plus every focused reference in the declared layout. | complete `skills/` inventory and routing tests |
| A3-D3 | Shared scripts for validation, Markdown→JSON, JSON→SQLite, and SQLite→JSON with stable exit codes, stdout/stderr, and diagnostics. | `plugins/raptor/scripts/` and CLI tests |
| A3-D4 | Generic source-profile registration/loading plus built-in Raptor profile, without consumer-name branches in shared code. | profile boundary and tests |
| A3-D5 | Positive/negative route tests from the Raptor corpus, including malformed Markdown, diagnostics, canonical conversion, JSON validation, SQLite validation/import/export, and unsupported routes. | plugin integration suite |
| A3-D6 | External consumer guide for supplying a profile and running consumer-owned fixtures/tests without copying them into Raptor. | plugin docs |
| A3-D7 | Deterministic schema-vendor refresh/check contract and manifest schema version/hash; CI proves an exact copy of authoritative source. | `_vendor/raptor_schema/`, `plugin-manifest.json`, drift gate |
| A3-D8 | Six focused execution agents and plugin-local registry with path/version constraints for every A3-supported route. | declared `agents/` inventory, registry, frontmatter validation |
| A3-D9 | Plugin contract validator covering the pinned v0.7 normative reference, registries, frontmatter, manifests, inventories, reference links, response schemas, and both client packages. | shared validation script and CI gate |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| A3-AC1 | Claude and Codex discovery both expose exactly `/raptor:import`, `/raptor:export`, `/raptor:validate`, and `/raptor:round-trip` and resolve each to the matching skill directory. |
| A3-AC2 | Every router chooses one focused reference from explicit input intent, rejects ambiguous routes, and invokes only shared scripts/package APIs. |
| A3-AC3 | Supported A3 routes execute end to end with deterministic canonical JSON, structured diagnostics, schema-version enforcement, and SQLite transaction behavior inherited from A1/A2. |
| A3-AC4 | `json-md` and round-trip return the documented A4-pending unsupported result; all three Dolt references and Dolt validation return the documented later-phase unsupported result. |
| A3-AC5 | Dolt future references contain interface semantics only; repository inspection finds no Dolt DDL, driver, connection code, fixture, placeholder directory, or integration test. |
| A3-AC6 | A temporary synthetic external profile registers through the public boundary without shared-code changes; no external fixture is committed. |
| A3-AC7 | Vendor check fails for changed, missing, extra, or hand-edited vendor files and stale schema-version/hash metadata. |
| A3-AC8 | The plugin contains no duplicate transformation logic across skills or clients, P3 asset, `NFT`, Rust SQLx, or bulk-migration workflow. |
| A3-AC9 | All four skills and six agents have valid versioned YAML frontmatter; registry path/version constraints resolve exactly and fail closed on mutation. |
| A3-AC10 | Each supported route delegates to exactly one focused agent; no monolithic agent selects among formats or returns raw tool output. |
| A3-AC11 | Every agent response is fenced JSON with the standard envelope and namespaced error object; malformed/unfenced responses are rejected and outputs contain no secrets or tool traces. |
| A3-AC12 | First-step CLI preflights and installation/troubleshooting references cover every external dependency; missing/old CLIs halt before delegation. |
| A3-AC13 | Path traversal/out-of-root paths are rejected; mutation defaults to validation/dry-run, explicit apply is required, and file/database changes are atomic. |
| A3-AC14 | Both client manifests package the identical complete A3 skill, focused-reference, agent, registry, script, and vendor inventory; CI fails any omission or extra unregistered agent. |
| A3-AC15 | CI validates implemented skill/agent/plugin invariants against the committed pinned v0.7 reference and never reads the mutable sibling checkout. |

## Authoritative validation

The README records the schema-vendor refresh/check operation without requiring a particular shell build filename. CI runs check mode before these gates:

```sh
python -m pip install -e 'schema[test]'
python -m pytest plugins/raptor/tests
python plugins/raptor/scripts/validate_plugin.py --guideline docs/plans/phase-a/references/claude-code-skills-agents-guidelines-v0.7.md --check-frontmatter --check-registry --check-manifests --check-inventory
git diff --exit-code -- plugins/raptor/_vendor/raptor_schema plugins/raptor/plugin-manifest.json
mkdir -p plugins/raptor/tests/.tmp
python plugins/raptor/scripts/validate.py markdown --profile raptor --input plugins/raptor/tests/fixtures/raptor --format json
python plugins/raptor/scripts/markdown_to_json.py --profile raptor --input plugins/raptor/tests/fixtures/raptor --output plugins/raptor/tests/.tmp/raptor-canonical.json --validate
python plugins/raptor/scripts/markdown_to_json.py --profile raptor --input plugins/raptor/tests/fixtures/raptor --output plugins/raptor/tests/.tmp/raptor-canonical.json --apply
python plugins/raptor/scripts/validate.py json --input plugins/raptor/tests/.tmp/raptor-canonical.json --format json
python plugins/raptor/scripts/import_sqlite.py --database plugins/raptor/tests/.tmp/phase-a.sqlite --input plugins/raptor/tests/.tmp/raptor-canonical.json --validate
python plugins/raptor/scripts/import_sqlite.py --database plugins/raptor/tests/.tmp/phase-a.sqlite --input plugins/raptor/tests/.tmp/raptor-canonical.json --apply
python plugins/raptor/scripts/validate.py sqlite --database plugins/raptor/tests/.tmp/phase-a.sqlite --format json
python plugins/raptor/scripts/export_sqlite.py --database plugins/raptor/tests/.tmp/phase-a.sqlite --source docs/requirements.md --output plugins/raptor/tests/.tmp/raptor-export.json --validate
test ! -e schema/sql/dolt
test ! -e plugins/raptor/tests/fixtures/dolt
rg --files plugins/raptor/tests | rg '(?i)(^|/)dolt([^/]*)(integration|fixture)|(^|/)(integration|fixture)[^/]*dolt' && exit 1 || true
rg -n '\b(doltpy|mysqlclient|pymysql|mysql-connector|sqlx)\b' schema/pyproject.toml Cargo.toml plugins/raptor/plugin-manifest.json && exit 1 || true
rg -n '^\s*(from|import)\s+(dolt|doltpy|mysql)|dolt://|mysql://' plugins/raptor/scripts schema/src && exit 1 || true
rg -n 'unsupported|RAPTOR\.UNSUPPORTED\.DOLT' plugins/raptor/skills/import/references/json-dolt.md plugins/raptor/skills/export/references/dolt-json.md plugins/raptor/skills/validate/references/dolt.md
```

Tests own and clean the repository-root `.tmp/` directory. Discovery/routing tests assert exact public command strings, every support-matrix cell, path rejection, validate/apply behavior, atomic failure behavior, fenced envelopes, redaction, registry mismatch, missing CLI handling, and package inventory equality.

## Traceability

| Deliverable | Phase requirements |
|---|---|
| A3-D1, A3-D2 | PA-REQ-006, PA-NFR-006 |
| A3-D3, A3-D4 | PA-REQ-004, PA-NFR-001, PA-NFR-004 |
| A3-D5 | PA-REQ-002, PA-REQ-003, PA-REQ-005, PA-REQ-009 |
| A3-D6 | PA-NFR-001 |
| A3-D7 | PA-NFR-004, PA-NFR-005 |
| A3-D8, A3-D9 | PA-REQ-006, PA-NFR-004, PA-NFR-006 |

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Routers duplicate business logic | skills contain routing/instructions only; Python implementation is centralized under `plugins/raptor/scripts/`. |
| Client packaging forks behavior | both manifests resolve the same exact four skills and shared assets. |
| Vendored models become a second authority | vendor is generated, hash-recorded, never hand-edited, and CI fails drift. |
| Future Dolt references imply false support | every Dolt route returns structured unsupported and code/DDL/driver absence is gated. |
| Parser scope expands to every repository | ship only Raptor profile; consumers own their profiles. |
| Missing agent/template assets ship in one client | manifest-derived inventory is compared across clients and against registry/filesystem in CI. |
| Tool output or credentials leak through agents | enforce response schemas, redact diagnostics, and forbid raw traces/secrets in agent contracts/tests. |
| Mutation escapes repository or leaves partial state | canonicalize against repo-root allowlist, validate by default, require apply, and use atomic writes/transactions. |

## Non-closure

- JSON→Markdown rendering and semantic round-trip execution; A4 owns both.
- Dolt/MySQL DDL, adapter, driver, connection, fixture, test, or placeholder directory.
- Consumer profile, fixture, test, or migration.
- Marketplace publishing, remote updates, telemetry, or fleet runner.
- Rust SQLx integration.

## Handoff to A4

A4 consumes the exact public command names, four routers, shared scripts directory, Raptor profile, schema vendor, and supported/unsupported matrix. It activates `json-md` and round-trip by adding shared templates and implementation, without changing command names or duplicating route logic. Dolt remains unsupported.
