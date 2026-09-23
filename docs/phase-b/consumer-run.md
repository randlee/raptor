# Consumer run

Read-only run at commit `6be9d2d5eae8d34499785c267cf4d5ae9b3b0236`.
The full JSON index remains untracked for hand-off to the operator.

| Measure | Result |
| --- | --- |
| Files scanned | 157 |
| Requirement rows | 537 |
| Decision rows | 51 |
| Extraction exit | 1 |
| SQLite load exit | 0 |
| Dump equals index records | no |
| Every emitted column non-null | no — `supersedes` and `superseded_by` are null |
| Detailed summary groups | 634 |

The detailed group table exceeds this report's 80-line ceiling. The table
below aggregates those groups by rule; section, label, and allowed values are
mixed within each aggregate. Counts are ordered descending.

| Rule | Section | Label | Count | Files | Allowed |
| --- | --- | --- | ---: | ---: | --- |
| UNKNOWN_LABEL | mixed | mixed | 1180 | mixed | mixed |
| MISSING_FIELD | — | — | 361 | 63 | — |
| BAD_VALUE | mixed | mixed | 345 | mixed | mixed |
| UNKNOWN_SECTION | mixed | mixed | 304 | mixed | mixed |
| MISSING_ID | — | — | 40 | 40 | — |
| DUPLICATE_ID | — | — | 10 | mixed | — |
| DANGLING_REFERENCE | — | mixed | 3 | mixed | — |

| Rule | B.3 | B.4 | This run |
| --- | ---: | ---: | ---: |
| UNKNOWN_LABEL | 1902 | not recorded | 1180 |
| MISSING_FIELD | 282 | not recorded | 361 |
| BAD_VALUE | 337 | not recorded | 345 |
| UNKNOWN_SECTION | 0 | not recorded | 304 |
| MISSING_ID | 40 | not recorded | 40 |
| DUPLICATE_ID | 39 | not recorded | 10 |
| DANGLING_REFERENCE | 2 | not recorded | 3 |

Own inventory: 2 files, 15 records, exit 0, with no diagnostics. The consumer
run still exits 1 with 2,243 diagnostics; its SQLite dump completes but does not
equal the index records.

The requirements index has 537 rows while its dump has 532: five duplicate
identifiers collapse through replacement on the primary key, retaining the
final occurrence. Decisions have 51 index rows and 51 dump rows with no
duplicate identifiers. This is a corpus condition, not a loader round-trip
defect.
