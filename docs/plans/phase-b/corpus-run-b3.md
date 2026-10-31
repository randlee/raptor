# B.3 historical corpus observation

Read-only corpus snapshot: `6be9d2d5eae8d34499785c267cf4d5ae9b3b0236`.
Historical extraction exited 1: 157 files, 675 records (537 requirements,
138 decisions), 2,602 diagnostics and 389 summary groups.

| Rule | Historical count |
| --- | ---: |
| BAD_VALUE | 337 |
| DANGLING_REFERENCE | 2 |
| DUPLICATE_ID | 39 |
| MISSING_FIELD | 282 |
| MISSING_ID | 40 |
| UNKNOWN_LABEL | 1091 |
| UNKNOWN_SECTION | 811 |

The original 412-line report violated its 60-line ceiling and contained
source-specific labels. Its complete table is preserved in the external
historical evidence bundle, not copied into this neutral summary.
Original report SHA-256: `5061fc5fae3c5870b43dc53f9c690ec165900bd42369576ffec58bd0be370c57`.

Every historical group had null section attribution; no canonical section
can be reconstructed from that report alone. This remains an explicit
historical evidence gap, rather than an inferred successful run.
The corrected section-aware importer and full-object comparison are covered
by [the B.6 report](consumer-run-b6.md); final phase approval remains open.
