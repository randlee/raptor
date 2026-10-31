# Consumer run B.6 — provisional comparison

Extractor: `d8f1e1174c3f5529e2c6bef999f382bbf6211b47`.
Baseline extractor: `0fd132c50c7fc4f9136e0cea67bdf39865b64025`.
Document commit: `6be9d2d5eae8d34499785c267cf4d5ae9b3b0236`.
This evidence precedes pending SQL-constraint and diagnostic-section fixes.
A fresh extension build and pinned rerun are required before final acceptance.
The pinned document snapshot was read without modifying its checkout.
Extraction returned 1; SQLite loading and dumping returned 0.

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
| Diagnostics | 2243 | 3125 |
| Summary groups | 634 | 548 |
| UNKNOWN_LABEL | 1180 | 1102 |
| MISSING_FIELD | 361 | 1267 |
| BAD_VALUE | 345 | 395 |
| UNKNOWN_SECTION | 304 | 304 |
| MISSING_ID | 40 | 40 |
| DUPLICATE_ID | 10 | 2 |
| DANGLING_REFERENCE | 3 | 15 |

Classification uses the exact directory component `rendered`.
Zero matching files means the planned rendered corpus is absent; 0 of 0
provides no consumer round-trip evidence. No aliases were applied.

Full before-and-after record occurrences and diagnostic groups are retained
in the external evidence bundle. Source matching uses unique heading identity,
exact content witnesses for duplicate headings, and bijection after those
witness assignments for the remaining empty occurrences. Each occurrence is
qualified independently with its original document header. The resulting
ordered row arrays exactly equal the emitted index. This avoids attributing
one duplicate occurrence's diagnostics to another occurrence sharing its id.

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

The first three mechanisms account for 238 occurrences under the documented
strict-content, scalar, and whitespace causes. The remaining 175 have known
source mechanisms but lack complete attribution under the six permitted causes;
they are not accepted as equivalent. Additional diagnostic categories alone
would not establish equivalence of the changed record content.
The 395 BAD_VALUE diagnostics arise from 309 unsupported heading kinds,
53 scalar failures, 30 detached-prose reports, and 3 malformed-item reports.
The evidence includes diagnostic-to-code function mappings and artifact hashes.

There are 408 changed dump rows. Their source mechanisms are: required content
206; scalar validation 15; whitespace 12; thematic breaks 107; other content
reconstruction 58; detached prose 8; malformed placeholders 1; duplicate winner
selection after rejection 1. Every dumped row exactly equals the last index
occurrence for its id. One surviving duplicate reduces the candidate requirement
count by one; replacement also changes array order.

At this source revision, section grouping is incomplete; group sections are null.
All 299 changed summary groups are backed by complete diagnostic occurrence
lists and source references. Both old and new group counts and location lists
were verified exactly against their constituent diagnostic objects. Vocabulary,
label scope, item validation, row rejection, and source location changes remain
visible; full permitted-cause attribution of these group deltas is incomplete.

Rendered text reconstruction defects discovered during comparison were corrected:
scalar bullets and paragraph gaps are preserved, fenced syntax stays literal,
and list continuations retain their parent item. Templates now indent multiline
list continuations, distinguishing their paragraphs and code from detached prose.
The Python suite passes 49 tests, including the new round-trip regressions.

Acceptance remains incomplete: the rendered consumer corpus is absent, 175 index
occurrences still require acceptance treatment, and the 299 changed diagnostic
groups require completed causal attribution. Existing evidence was preserved;
this report does not claim a passing consumer comparison.
