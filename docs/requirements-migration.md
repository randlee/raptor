# Raptor Corpus Migration Requirements

Status: planned after Phase A. These requirements define the next migration
boundary; they do not claim that the completed Phase A implementation already
satisfies them. The owning phase plan must map every requirement below to a
production-ready sprint, evidence, and acceptance gate before implementation.

## Normative definitions

### Authorized corpus

The authorized corpus is the sorted set of repository-relative regular files
selected by a validated repository manifest, scan configuration, routing
configuration, identity manifest, and resolved format declarations. A symlink,
unregistered document, unmatched file, multiply matched file, or file outside a
declared source is not part of the corpus and may not be read by ingress.

### Source content unit

A source content unit is one ordered, typed byte interval produced by the
versioned Markdown consumer. Unit kinds are frontmatter, heading, paragraph,
list, table, fenced code, thematic break, link definition, HTML/comment, blank
separator, and unsupported. Units use zero-based half-open UTF-8 byte offsets.
For each source file, intervals must be non-overlapping, contiguous, begin at
zero, and end at the file byte length. The stable unit ID is the lowercase
SHA-256 of the canonical JSON array
`[repository_id, document_id, source_sha256, start_byte, end_byte, kind]`.
Canonical JSON bytes use Raptor's existing encoder: UTF-8, lexicographically
sorted object keys, compact separators, finite JSON numbers, and normalized
negative zero, with no trailing newline.

Whitespace and comments are units. An implementation may classify them as
presentation-only, but it may not omit them from accounting. A unit containing
semantic text, metadata, a link target, code, a table cell, or an identifier is
content-bearing. Unsupported units are errors; the migration authority cannot
relabel them as presentation-only to make reconciliation pass.

### Reconciliation ledger

The versioned reconciliation ledger is canonical JSON with:

- `ledger_version`, `repository_id`, `input_revision`, and `input_tree_sha256`;
- one `sources` entry per authorized path containing `document_id`,
  `content_sha256`, byte length, ordered unit IDs, and route identity;
- one `units` entry per unit containing its ID, kind, byte interval, byte hash,
  and exactly one disposition;
- `canonical` disposition with one or more canonical JSON Pointers and a
  transformation record for each pointer;
- `preserved` disposition with one or more namespaced extension JSON Pointers
  and a transformation record for each pointer;
- `rejected` disposition with a stable diagnostic code;
- one `derivations` entry for every canonical leaf not sourced from Markdown,
  containing its JSON Pointer, derivation kind (`configuration`, `identity`,
  `source_digest`, or `generated`), authoritative input path or evidence ID,
  authoritative input SHA-256, allowlisted derivation rule ID and exact version,
  and canonical target-value digest;
- canonical document/artifact keys and digests after import and after export;
- source-to-output document and artifact lineage;
- the staged output tree digest and compatibility evidence reference.

Each transformation record contains the source unit IDs, transform ID and exact
version, canonical JSON digest of the normalized source value, target JSON
Pointer, and canonical JSON digest of the target value. Reconciliation reruns
the allowlisted deterministic transform from the recorded source bytes and
requires both value digests to match. An identity transform requires equal
digests. A non-identity transform must return the exact recorded pointer/value
pairs; a pointer not produced by that rerun is unaccounted. Assigning a unit to
unrelated or additional pointers therefore cannot increase coverage.

Derivation records use the same proof boundary. Reconciliation loads the
verified authoritative input, reruns the allowlisted exact-version derivation
rule, and requires the rule to produce the recorded JSON Pointer and canonical
target-value digest exactly. An unversioned rule, missing input, extra output,
or value mismatch is unaccounted; the `generated` kind is not an escape from
deterministic re-execution.

An accepted import contains no `rejected` disposition. Every source byte belongs
to exactly one unit, every unit has exactly one disposition, every referenced
JSON Pointer exists, and every content-bearing canonical leaf has exactly one
authority: at least one source unit or one typed derivation record. Repository
and document identity derive from the validated manifest and identity entry;
origin content hash derives from the complete source bytes; generated
materialization values use typed derivation records. Reconciliation is exactly
100% only when all four predicates hold; percentages rounded from a partial
result are invalid.

### Deterministic evidence digests

All evidence hashes are lowercase SHA-256 over canonical bytes. Canonical JSON
encoding is the encoder defined under Source content unit. A corpus tree
digest hashes the canonical JSON array of `[path, byte_length, content_sha256]`
entries for exactly the authorized corpus (input) or declared staged corpus
(output), sorted by normalized repository-relative POSIX path. Paths are UTF-8
RepositoryPath values; symlinks, directories, control state, stages, backups,
and files outside the declared corpus are rejected rather than hashed.

An invocation argument digest hashes the canonical JSON array of the exact argv
strings passed without a shell after repository/staging placeholders are
resolved to normalized repository-relative POSIX paths. The executable is bound
separately by its resolved regular-file path and byte SHA-256. Environment
variables are absent unless an evidence schema version defines an explicit
allowlist and records each included name and value hash.

### Canonical comparison and exclusions

Canonical comparison uses deterministic Pydantic JSON dumps and preserves list
order wherever the model declares a list. Object key order is irrelevant.
Set-like projections are sorted before comparison. Repository, document, and
artifact identity; immutable origin; artifact payloads; relationships;
extensions; and authorial list order are content-bearing.

Only `source_location` and `provenance.materialization` may differ after render
and reparse. Those values are not ignored: the renderer must validate the
documented provenance transition, output path, parent hash, output content hash,
profile identity, and template identity independently. No other field is an
implicit transport exclusion.

### Corpus lineage

A file split or combination is unsupported until a versioned corpus-lineage
model is implemented. That model must bind every input `DocumentKey` to one or
more output `DocumentKey` values, and every input `ArtifactKey` to exactly one
output `ArtifactKey`. It must define document-ID allocation, immutable-origin
retention for multiple inputs, identity-manifest updates, persistence ownership,
and comparison semantics. Apply must reject split/combine output while any of
those rules is absent. A one-to-one file rewrite uses the existing document
identity and provenance transition.

### Compatibility evidence

Compatibility evidence is versioned canonical JSON containing the migration
authority ID, validator/build tool IDs and versions, resolved executable path
and byte digest, normalized argument digest, exact input revision, input tree
digest, staged tree digest, start/end times, exit status, error and warning
counts, and stdout/stderr digests for each gate.

For this phase, Raptor must invoke every gate directly without a shell, capture
the result, and create the evidence; imported self-reported evidence is not
accepted. The migration authority supplies an explicit `MigrationTrustPolicy`
operation input containing `policy_version`, `authority_id`, and a non-empty
`tools` list. Each tool entry contains its gate role, tool ID, exact version,
verified tool-bundle digest, executable digest, optional interpreter digest,
exact normalized `argv` array, and working-directory role (`repository_root` or
`staging_root`). `argv` is a complete array: token count, order, and value must
match exactly after path normalization. Regex, glob, shell syntax, placeholders,
prefix matching, and trailing arguments are unsupported. Unknown fields and
floating versions are invalid. The policy file's canonical SHA-256 is recorded
in every compatibility result.

Raptor invokes only tools allowlisted by that policy. Before invocation it copies
the verified executable, scripts/modules in the declared tool bundle, and any
declared interpreter into a newly created private read-only execution directory,
using no-follow regular-file handles; it fsyncs and rehashes the copies. Script
execution uses the verified interpreter copy explicitly rather than a shebang or
`PATH`. The child uses the recorded working directory, receives empty stdin, a
closed inherited-file-descriptor set, and only the versioned environment
allowlist. Raptor rehashes the private bundle after execution and rejects any
identity or byte change. It recomputes tree, bundle, binary, interpreter,
argument, working-directory, stdin, environment, and result bindings before
apply. A future remote gate requires a separately versioned cryptographic
attestation contract and is unsupported here. Consumer-specific commands and
fixtures remain outside Raptor-owned product artifacts.

## Functional requirements

### REQ-RAP-013 — Repository-root corpus ingress

Raptor shall execute corpus ingress from the repository root using only the
validated configuration artifacts and fields enumerated in
`docs/configuration.md`.

Acceptance: one validate-mode operation loads the manifest-selected scan,
routing, and identity artifacts plus every selected format declaration;
propagates the selected identity path through identity, locking, rendering,
transaction, and recovery calls; produces the authorized corpus and initial
ledger without mutation; and rejects every configuration or inventory error
before parsing source content. Database destination, credentials, mode,
reference resolution, and staging paths are explicit operation inputs.

### REQ-RAP-014 — Total schema-to-sc-compose projection

Raptor shall generate complete Markdown documents only through sc-compose using
a versioned, hash-verified template set and JSON-compatible projection derived
from a validated canonical document.

Acceptance: a generated canonical-leaf inventory proves that every
content-bearing leaf in every artifact family appears in the projection and is
recovered after render/reparse. Python may validate, serialize canonical JSON,
and compute projection values; it may not assemble the complete Markdown
document, headings, sections, or provenance wrapper. Missing leaves, unused
projected leaves, undefined template values, and output created without the
sc-compose invocation are errors.

### REQ-RAP-015 — Lossless corpus round trip

Raptor shall reconcile the complete authorized corpus through Markdown,
canonical JSON, reference persistence, canonical JSON, and sc-compose Markdown
without silent content loss.

Acceptance: the ledger satisfies the 100% accounting invariant; import and
export canonical digests match; render/reparse differs only by the enumerated
transport values with a valid provenance transition; and every source-to-output
mapping satisfies the implemented lineage mode. Unsupported units and
unsupported split/combine mappings fail before import or apply.

### REQ-RAP-016 — External render compatibility gate

Raptor shall require trusted compatibility evidence for both the accepted input
corpus and the exact staged rendered corpus before replacement.

Acceptance: both evidence records satisfy the compatibility-evidence contract,
report zero errors and zero warnings, and include a successful document-rendering
or site-build gate. Apply recomputes the revision and tree bindings and fails on
any mismatch. The staged bytes authorized by evidence are the only bytes eligible
for replacement.

## Non-functional requirements

### NFR-RAP-008 — Fail-closed migration evidence

Ingress, canonicalization, persistence, export, projection, rendering, reparse,
reconciliation, and external compatibility shall each emit deterministic,
auditable boundary evidence and fail closed.

Acceptance: the ledger records input and output paths and hashes, unit coverage,
diagnostics, canonical keys and digests, persistence counts, lineage, and
compatibility evidence. Each downstream record includes the upstream digest it
consumed. A missing, stale, reordered, or mismatched record prevents apply.
