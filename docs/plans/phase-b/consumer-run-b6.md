# Consumer run B.6 — audited strict duplicate comparison

Runtime proof SHA: `fc961ce19f605a209c9e09650bbacf6d4cf782c8`.
Baseline extractor: `0fd132c50c7fc4f9136e0cea67bdf39865b64025`.
Document commit: `6be9d2d5eae8d34499785c267cf4d5ae9b3b0236`.
Fresh source archive, environment, extension and empty build target were used.
All 949 pinned document files were byte-verified; the checkout was read-only.

| Measure | Historical baseline | Candidate |
| --- | ---: | ---: |
| Scanned files | 157 | 157 |
| Original rendered files | — | 0 |
| Hand-written files | — | 157 |
| Index requirements | 537 | 308 |
| Index decisions | 51 | 30 |
| Raw index load exit | 0 | 1 |
| Raw dump requirements | 532 | not attempted |
| Raw dump decisions | 51 | not attempted |
| Derived unique subset dump requirements | — | 308 |
| Derived unique subset dump decisions | — | 30 |
| Diagnostics | 2243 | 3207 |
| Summary groups | 634 | 555 |
| UNKNOWN_LABEL | 1180 | 1114 |
| MISSING_FIELD | 361 | 1273 |
| BAD_VALUE | 345 | 399 |
| UNKNOWN_SECTION | 304 | 304 |
| MISSING_ID | 40 | 39 |
| DUPLICATE_ID | 10 | 64 |
| DANGLING_REFERENCE | 3 | 14 |

Extraction exits 1. The baseline SQL counts describe historical behavior only;
they do not authorize selecting a duplicate winner. No raw dump was fabricated.
Original rendered classification uses the exact directory component `rendered`.
Its zero count is observational; a nonzero requirement was withdrawn.
No aliases were applied.

Source inventory detects 30 duplicated identifiers across 64 valid headings,
including 48 occurrences already rejected for content. Every occurrence reports;
all matching rows are omitted. Against `226910f`, exactly 16 previously accepted
rows disappear: 4 requirements and 12 decisions. Before duplicate finalization,
qualified rows equal that prior index exactly. Every retained full object and
its relative order is unchanged. Complete removed-row and sibling witnesses exist.
Rust separately rejects both occurrences of the submitted duplicate sample.

The raw duplicate-bearing index fails loading before database connection:
a new database remains absent; an existing fixture database remains byte- and
mtime-identical, with no journal created. There is no first/last projection.
A separately labelled unique retained subset loads and dumps all 338 rows exactly,
without editing values. A unique fixture update preserves rowids and updates
its intended value. These derived successes do not validate the raw index.

All 3129 non-inventory diagnostics equal `226910f` as full occurrence multisets.
Its 2 duplicate reports become 64 source reports. Two dangling reports disappear
with an omitted row; one new report targets an omitted identifier, leaving 14.
Four full summary-group objects differ; their counts and locations re-aggregate
exactly from the source-backed diagnostics. All changes have duplicate-policy
witnesses; no unrelated retained-data or parser drift is accepted.

| Current baseline occurrence difference mechanism | Count |
| --- | ---: |
| Required content rejection | 199 |
| Scalar validation rejection | 15 |
| Whitespace only | 9 |
| Strict duplicate policy | 27 |
| Hyphen thematic break removal | 107 |
| Other content reconstruction | 48 |
| Detached list prose rejection | 8 |
| Malformed placeholder rejection | 1 |
| Total changed baseline occurrences | 414 |

The duplicate category includes 11 previously content-rejected occurrences and
16 newly excluded accepted rows. Current nonduplicate changed mechanisms total
164. The user approved the original 175 historical parser corrections on
2026-10-30 ("yes/yes"), including the documented diagnostic-contract changes.
Duplicate exclusion of 11 cases remains separately governed by strict rejection.
All 978 changed full baseline groups retain complete before/after occurrence proof.
There is no candidate raw-dump delta because the raw load is correctly rejected.

A derived corpus renders each of the 338 unique retained occurrences separately.
All 338 documents qualify without source diagnostics; full ordered qualified and
accepted arrays equal their input. Entire acceptance results match, with only
the same 14 dangling-reference errors and no duplicate errors. This covers
retained rows only, while original rendered-file count remains 0.

Earlier proof covers structural headings, section attribution, Rust-owned heading
validation, source offsets and strict schema contracts. The historical pre-B.4
rule table and later summary disagree on classification, but agree in total.
At final candidate `52249dc`, 102 Python tests and 59 Rust tests plus 5 doctests
pass; all nine CI jobs pass. The official 0.8.0 function audit and per-file caps
pass. The pre-existing CLI line is 108 characters; integrated lint is not claimed.

The user accepted this audited B6 before/after proof in place of missing historical
per-group reports and accepted the documented additional parser corrections on
2026-10-30 ("yes/yes"). Historical reports are not recreated or relabelled.
The narrow generated-schema/metadata and diagnostic Value exceptions were also
approved. Final quality-manager verification remains required; strict duplicate
rejection and existing per-file limits remain in force.
Evidence summary SHA-256:
`1b0a61e31d761c0a1d31998369d340c626814bb2096254bfb5e898bb0dc57b26`.
