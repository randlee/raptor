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

The built-in reference extractor is the only parser. It recognizes level-two
`## REQ|NFR|ADR-<scope>-<four digits>: <title>` items and preserves their
verbatim content, nested sections, raw reference tokens, and source order.
Malformed headings (including a non-colon separator) fail with
`RAPTOR.REFERENCE.MALFORMED_HEADING`; invalid UTF-8, duplicate item headings,
unsupported statuses, and ordinary selected files without an item fail closed
with `RAPTOR.REFERENCE.INVALID_UTF8`,
`RAPTOR.REFERENCE.DUPLICATE_HEADING`, `RAPTOR.REFERENCE.UNSUPPORTED_STATUS`,
and `RAPTOR.REFERENCE.NO_ITEM`. A plain level-two heading inside an item body is
body text of that item.
Configured design-document and test-plan routes each yield one generic record:
verbatim `content` is the complete Markdown, the envelope is empty, and nested
headings and mentions are derived from content. Design uses its registered
document ID. A test plan uses the start of a declared bold `Test Plan ID` single
ID or `A through B`/`A to B` range, retaining the range in metadata; otherwise it
uses the registered document ID. Their first preamble bold Status is stored only
when it is one of the six supported spellings; otherwise status is null without
a diagnostic. Relationships are emitted raw and SQLite resolves a target only
when it is unique in the repository.

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

`.raptor/sources.toml` is the inventory: Raptor never discovers arbitrary
directories outside that explicit selected list. The default built-in `raptor`
template set, not a consumer external set, renders SQLite/JSON exports.

JSON→Markdown uses the five inventoried strict templates and requires
`sc-compose >=1.6.1,<2.0.0`. Stored-document rendering uses the bounded journal
under `.raptor/transactions/`: pre-identity crashes roll back, while
post-identity crashes retry the idempotent SQLite write. The immutable origin is
preserved and the rendered materialization records the parent content hash and
template identity. Consumer template sets live under
`.raptor/template-sets/`; see [template-sets.md](template-sets.md).

All Dolt routes remain unsupported. No Dolt implementation is included here.
