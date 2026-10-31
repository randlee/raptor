# B.4 corpus run

The configured corpus run exits non-zero when diagnostics are present. The
table below records the ordered diagnostic groups from the prior run and this
schema pass; no source document is changed by this sprint.

| Diagnostic group | Before | After |
| --- | ---: | ---: |
| Missing field | 282 | 361 |
| Invalid value | 337 | 345 |
| Unknown section | 811 | 304 |
| Unknown label | 1091 | 1180 |
| Duplicate identifier | 39 | 10 |
| Dangling reference | 2 | 3 |

The two corrected Before counts are summed from the preserved original B.3
table, SHA-256 `5061fc5fae3c5870b43dc53f9c690ec165900bd42369576ffec58bd0be370c57`.
This is a factual classification correction, not a reconstructed run. These
aggregates do not supply the missing historical per-group comparison.

The B.4 fixture round trip is validated by the automated Rust and Python
suite, including same-table supersession foreign keys and group parsing.
The detailed per-group table exceeds this report's 70-line ceiling; the fresh run has 634 groups.
