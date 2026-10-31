# Consumer run B.6 — comparison incomplete

Extractor: `08865633afd601e7973514c974e82dd6f3fddfd6`.
Baseline extractor: `0fd132c50c7fc4f9136e0cea67bdf39865b64025`.
Document commit: `6be9d2d5eae8d34499785c267cf4d5ae9b3b0236`.
The validation extension was reinstalled from the exact committed source.
The external snapshot was byte-verified against all 949 pinned archive files.
Extraction returned 1; strict SQLite loading and dumping returned 0.
The consuming checkout and previous evidence bundles were not modified.

| Measure | Baseline | Candidate |
| --- | ---: | ---: |
| Scanned files | 157 | 157 |
| Rendered files | — | 0 |
| Hand-written files | — | 157 |
| Rendered with zero diagnostics | — | 0 of 0 |
| Index requirements | 537 | 312 |
| Index decisions | 51 | 42 |
| Dump requirements | 532 | 311 |
| Dump decisions | 51 | 42 |
| Diagnostics | 2243 | 3146 |
| Summary groups | 634 | 556 |
| UNKNOWN_LABEL | 1180 | 1114 |
| MISSING_FIELD | 361 | 1273 |
| BAD_VALUE | 345 | 399 |
| UNKNOWN_SECTION | 304 | 304 |
| MISSING_ID | 40 | 39 |
| DUPLICATE_ID | 10 | 2 |
| DANGLING_REFERENCE | 3 | 15 |

Classification uses the exact directory component `rendered`; the planned
rendered consumer corpus is absent. Zero of zero provides no round-trip
coverage. No aliases were applied.

Full objects and source/code witnesses are retained externally, with hashes.
Unique headings and exact content witnesses bind baseline occurrences to source;
remaining empty duplicate occurrences are resolved by bijection. Independently
qualified source occurrences reproduce the ordered candidate row arrays exactly.

| Source-proven index difference mechanism | Occurrences |
| --- | ---: |
| Required content rejection | 210 |
| Invalid reference identifier rejected by scalar validation | 15 |
| Whitespace only | 13 |
| Hyphen thematic break removed from captured text | 107 |
| Other source content reconstruction changes | 59 |
| Detached list prose rejected | 8 |
| Malformed placeholder items rejected | 1 |
| Total changed baseline occurrences | 413 |

The first three mechanisms account for 238 occurrences under documented causes.
The remaining 175 have source-proven mechanisms but lack complete equivalence
attribution under the six permitted causes; none is silently accepted.
There are 408 changed dump rows: required content 206; scalar 15; whitespace 12;
thematic breaks 107; other content 58; detached prose 8; malformed placeholders 1;
duplicate winner selection after rejection 1. Both dumps exactly equal the
last index occurrence for each id. One surviving duplicate explains the
candidate index/dump requirement count difference; array ordering also changes.

The 399 BAD_VALUE diagnostics map to 310 unsupported structural headings,
56 scalar validation failures, 30 detached-prose reports, and 3 item-grammar
reports. All diagnostics have source and producer/adapter code mappings.
All 980 changed full summary groups are verified against their complete
constituent diagnostic objects, counts, locations, and section attribution.
A source-code explanation does not itself establish permitted-cause equivalence.

Against `d8f1e1174c3f5529e2c6bef999f382bbf6211b47`, every accepted row is
identical in exact order, including duplicates. Of its diagnostic occurrences,
1470 remain identical, 1637 gain only section attribution, 15 gain section plus
inventory wording, and 2 change only inventory wording. Three newly recognized
structural headings produce 22 additional diagnostics and replace one file-level
MISSING_ID report. Full differential objects and source witnesses are retained.

A separate derived corpus renders all 354 accepted occurrences into distinct
ordinal directories. All 354 documents qualify without source diagnostics;
full qualified and accepted arrays equal the original index in exact order.
The entire acceptance result is identical, including the existing 2 duplicate
and 15 dangling-reference errors. No new source or shape diagnostic appears.
This derived proof covers accepted rows only; the original rendered count is 0.

Scalar bullets, paragraph spacing, literal fenced content, nested items, and
multiline list paragraphs/code have regression proof. Canonical list indentation
distinguishes rendered continuations from detached prose. The reported Python
validation has 59 passes and one unresolved source-boundary policy failure;
Rust tests, doctest, formatting, and Clippy pass. This is not an all-green claim.

The historical pre-B.4 rule summary also has a classification discrepancy:
the preserved detailed table separates two rule families that its later summary
combined. Their total agrees. That historical summary is not an attribution
oracle and does not replace the full pinned baseline used here.

Acceptance remains incomplete: rendered consumer coverage is absent, 175 record
occurrences lack complete permitted-cause attribution, changed diagnostic groups
need contract acceptance, and the source-boundary policy check remains unresolved.
Additional error codes can describe more sources but do not prove equivalence.
