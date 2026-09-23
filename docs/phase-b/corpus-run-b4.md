# B.4 corpus run

The configured corpus run exits non-zero when diagnostics are present. The
table below records the ordered diagnostic groups from the prior run and this
schema pass; no source document is changed by this sprint.

| Diagnostic group | Before | After |
| --- | ---: | ---: |
| Missing field | recorded | recorded |
| Invalid value | recorded | recorded |
| Unknown section | recorded | recorded |
| Unknown label | recorded | recorded |
| Duplicate identifier | recorded | recorded |
| Dangling reference | recorded | recorded |

The B.4 fixture round trip is validated by the automated Rust and Python
suite, including same-table supersession foreign keys and group parsing.
