# Raptor plugin operations

Run these commands with the interpreter where `raptor-schema` is editable-installed
(CI installs it explicitly; use the project Python 3.11 environment locally).

Sprint A5 provides eight routes: Markdown→JSON, JSON→SQLite, SQLite→JSON,
JSON→Markdown, migration round-trip, and validation for Markdown, JSON, and
SQLite. Every command validates by default; pass `--apply` to authorize its
declared mutation.

Markdown repositories register durable identities in `.raptor/identity.json`:

```sh
python plugins/raptor/scripts/identity.py register \
  --repo-root . --repository-id urn:raptor:repo:example \
  --document-id DOC-RAP-001 --path docs/requirements.md --apply
```

When a migration authority reports that the identity is already owned elsewhere,
pass `--registered-repository-id <owner>`; a differing owner fails with
`RAPTOR.IDENTITY.REUSE` before mutation.

The built-in `raptor` Markdown profile is always available. A consumer may keep
its own profile at `.raptor/profiles/<profile-id>/<version>/profile.json`, with an
entrypoint and SHA-256 for a declaration in that same version directory. The
declaration is strict JSON containing only `kind: raptor-markdown-profile`, its
profile ID, and version; executable consumer code is not loaded. External
profiles still require `--allow-profile-code`, API version `1`, and no symlink or
root escape. Raptor does not copy consumer profiles into the plugin.

Reference modes are explicit. Markdown defaults to `document`; JSON defaults to
`structural`. Use `batch` for a directory whose documents refer to one another,
or `store --database <relative-path>` to resolve targets already in SQLite.
Directory Markdown import defaults to `batch` and writes one canonical JSON file
per registered document ID. Empty directories and non-batch directory modes are
rejected.

## Configured batch ingress

Configured batch ingress is hosted by the existing `markdown_to_json.py` thin
wrapper. It reads only the explicit `.raptor/raptor.toml` manifest and the scan,
routing, and identity artifacts selected by that manifest; it never falls back
to a repository-wide scan. The database and report destinations are explicit.

```sh
python plugins/raptor/scripts/markdown_to_json.py \
  --repo-root . \
  --config .raptor/raptor.toml \
  --database .raptor/state/ingress.sqlite \
  --report .raptor/state/ingress-report.json \
  --apply
```

Without `--apply`, the same invocation validates the selected inventory and
returns the deterministic report in its JSON envelope without writing SQLite or
the report file. With `--apply`, the report records exactly one `imported` or
`diagnosed` terminal outcome per selected path. Any diagnosed path aborts the
SQLite publish, so a batch never partially applies; the report is retained for
operator review. The report is a versioned Raptor Pydantic contract and its
generated JSON Schema is checked with the canonical schema/vendor drift gates.

The native Markdown profile recognizes `REQ`, `NFR`, `ADR`, `DES`, and `TST`
artifact headings. Design bodies use `Overview:`, a pipe-separated `Component:`
(`name | responsibility`), optional comma-separated `Dependencies:`, and
`Interface:` (`name | description | participants`).
Test-plan bodies use `Objective:`, `Scope:`, `Test Case:`
(`id | title | semicolon-separated steps | expected result`), `Verifies:`, and
`Exit Criteria:`. There is no embedded-canonical-JSON escape hatch.

JSON→Markdown uses the five inventoried strict templates and requires
`sc-compose >=1.6.1,<2.0.0`. Stored-document rendering uses the bounded journal
under `.raptor/transactions/`: pre-identity crashes roll back, while
post-identity crashes retry the idempotent SQLite write. The immutable origin is
preserved and the rendered materialization records the parent content hash and
template identity. Consumer template sets live under
`.raptor/template-sets/`; see [template-sets.md](template-sets.md).

All Dolt routes remain unsupported. No Dolt implementation is included here.
