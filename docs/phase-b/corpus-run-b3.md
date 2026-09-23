# B.3 corpus run

The read-only run against the consumer repository at commit `6be9d2d` exited
`1`. It scanned 157 files and bound 675 records. The full JSON is untracked
and retained for the operator; this bounded table aggregates groups with the
same rule and allowed set. `multiple` preserves the number of distinct labels.

| Rule | Section | Label | Count | Files | Allowed |
| --- | --- | --- | ---: | ---: | --- |
| BAD_VALUE | — | multiple (4 distinct) | 337 | 23 | — |
| DANGLING_REFERENCE | — | Related | 2 | 1 | — |
| DUPLICATE_ID | — | — | 39 | 1 | — |
| MISSING_FIELD | — | — | 88 | 11 | — |
| MISSING_ID | — | — | 40 | 40 | — |
| UNKNOWN_LABEL | — | multiple (12 distinct) | 35 | 10 | Acceptance Criteria; Test Evidence |
| UNKNOWN_LABEL | — | multiple (18 distinct) | 20 | 5 | Key Considerations |
| UNKNOWN_LABEL | — | multiple (39 distinct) | 229 | 105 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | multiple (39 distinct) | 47 | 12 | — |
| UNKNOWN_LABEL | — | multiple (4 distinct) | 4 | 2 | Requirements; Architecture Decisions; Design Documents; Work Items; External References |
| UNKNOWN_LABEL | — | multiple (5 distinct) | 6 | 3 | Requires; Related |
| UNKNOWN_LABEL | — | multiple (64 distinct) | 418 | 50 | ID; Title; Status |
| UNKNOWN_LABEL | — | multiple (89 distinct) | 332 | 23 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_SECTION | — | multiple (42 distinct) | 664 | 31 | Related Documents |
| UNKNOWN_SECTION | — | multiple (69 distinct) | 147 | 16 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
