# Sprint B2 — Manifest-Driven Corpus Ingress

## Objective and stack

Close deterministic repository-root ingress before any source content is parsed.

- `gh-stack` branch: `phase-b/02-manifest-corpus-ingress`
- Relation: `must_follow B1`
- Merge-forward: merge pushed B1 development before every B2 development/fix round; B1 PR merges first.
- Parallel safety: not parallel-safe; ingress emits B1 source/route/operation receipts consumed by B3.

## Runtime contract

One importable runtime entry point accepts the repository root and explicit migration-input path:

```python
def prepare_corpus_ingress(
    repository_root: Path,
    operation_input_path: RepositoryPath,
) -> IngressSnapshot: ...
```

It loads `.raptor/raptor.toml`, then exactly its selected scan, routing, and identity files; verifies repository-ID agreement; resolves every route to `.raptor/profiles/<profile-id>/<profile-version>/profile.json` and the adjacent hash-pinned declaration it names; verifies `input_revision` through the policy-pinned Git revision resolver; snapshots and hashes all configuration before traversal; inventories only regular no-follow files matched by exactly one source; joins every file to one route and identity entry; sorts by normalized repository-relative POSIX path; and emits the initial ledger and `IngressSnapshot`. All configuration/inventory errors are returned together in deterministic path/code order before any Markdown bytes are passed to a profile.

B2 resolves the Phase A profile ambiguity explicitly: routed profiles are declarations selecting a registered implementation by exact `(profile_id, profile_version, api_version, module_sha256)`. Built-in Raptor and explicitly trusted repository-local implementations use the existing A4 registry/loader; the declaration never names an arbitrary import string. Repository-local executable code still requires the existing explicit trust opt-in and hash check. No network discovery or installed-package fallback is allowed.

The manifest-selected identity path is threaded through identity lookup/registration proposals, lock naming, render/transaction planning, and recovery APIs. Hardcoded `.raptor/identity.json` is removed from those runtime call sites; the default name remains only documentation/example data. Validate ingress never mutates identity.

## Authoritative deliverables

| ID | Deliverable |
|---|---|
| B2-D1 | `runtime/corpus.py` (or equivalent shared runtime module) implementing manifest/config/profile snapshot and deterministic authorized inventory. |
| B2-D2 | Exact profile declaration/registry/loading contract plus configuration and architecture documentation resolving the current disagreement. |
| B2-D3 | Selected identity-path propagation through existing identity, lock, rendering, transaction, and recovery APIs without changing Phase A identity semantics. |
| B2-D4 | Initial B1 ledger/source/route/config receipts and structured pre-parse diagnostics. |
| B2-D5 | Thin `migrate_corpus.py --validate-ingress` wrapper and existing round-trip agent/route wiring; no new public skill or agent. |

## Authoritative acceptance criteria

| ID | Criterion |
|---|---|
| B2-AC1 | One validate invocation from the repository root loads only the literal root manifest and its selected files, operation input, trust policy, exact Git revision, and routed profile declarations; missing, floating, or invalid inputs produce no fallback. |
| B2-AC2 | Inventory equals the sorted authorized corpus exactly; symlinks, control/state/stage/backup files, unmatched/unregistered/multiply matched files, overlapping roots, unavailable routes, and family mismatch fail before parsing. |
| B2-AC3 | Every inventory entry binds repository/document key, path, source declaration, exact profile ID/version/hash, byte length, and content digest in the initial ledger. |
| B2-AC4 | A spy profile proves no parse/canonicalize call occurs until all configuration, identity, profile, path, inventory, operation-input, and output-path checks pass. |
| B2-AC5 | Non-default manifest-selected identity paths work through lookup, lock, render planning, transaction, and restart recovery; tests fail any production hardcode of `.raptor/identity.json`. |
| B2-AC6 | Exact built-in and temporary neutral external profiles load through the existing trust/hash mechanism; ambiguity, floating/unsupported versions, API/entrypoint/hash/trust mismatch, path escape, and network/install fallback fail with stable codes. |
| B2-AC7 | Validate mode changes no source, configuration, identity, database, or stage path; its ledger/evidence output is deterministic when explicitly requested. |

## Required validation

```sh
python -m pytest plugins/raptor/tests/migration/test_ingress.py plugins/raptor/tests/profiles plugins/raptor/tests/recovery
python -m pytest schema/tests/models -k 'repository_config or scan_config or routing_config or identity'
python plugins/raptor/scripts/migrate_corpus.py --repo-root . --operation-input .raptor/operation-input/migration.json --validate-ingress
python plugins/raptor/scripts/validate_plugin.py --check-frontmatter --check-registry --check-manifests --check-inventory --check-vendor --check-templates
rg -n '"?\.raptor/identity\.json"?' plugins/raptor/runtime plugins/raptor/scripts && exit 1 || true
rg -n '\bNFT\b|sqlx|dolt://' plugins/raptor/runtime/corpus.py plugins/raptor/tests/migration && exit 1 || true
```

The command uses Raptor-owned operation-input fixtures added by the sprint; external-consumer assets are created only in temporary test directories.

## Traceability and non-closure

- B2-D1–D5 satisfy PB-REQ-002 / REQ-RAP-013 and the ingress portion of NFR-RAP-008.
- No byte-unit parser, transform proof, SQLite import/export orchestration, template change, split/combine apply, external gate execution, or certification.
- No Rust CLI, Dolt/MySQL, consumer fixture, or fleet scan.

## Handoff

B3 consumes only a validated immutable `IngressSnapshot` and its digest-linked initial ledger. It must not rescan, reroute, re-resolve identity, or reload a different profile declaration.
