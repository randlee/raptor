# B.3 corpus observation

Read-only run over the consumer repository at commit
`6be9d2d5eae8d34499785c267cf4d5ae9b3b0236`. Extraction exited `1`.
Scanned 157 files, bound 675 records, and emitted
2,602 diagnostics in 389 summary groups. Full JSON remains untracked.

| Table | Files with bound records | Records |
| --- | ---: | ---: |
| requirements | 45 | 537 |
| decisions | 50 | 138 |

File counts include only files contributing rows to the named table;
the scan total also includes files without bound records.
Each row below is one emitted summary group, in emitted order, without
aggregation. A dash represents null. Files is the size of the emitted
file map, including its empty-key bucket for diagnostics without provenance.
All emitted section values are null; no section context is inferred.
Six display labels replace the consumer identity prefix with `[consumer]`.
The full group table exceeds the planned 60-line report ceiling.

| Rule | Section | Label | Count | Files | Allowed |
| --- | --- | --- | ---: | ---: | --- |
| BAD_VALUE | — | Architecture Decisions | 15 | 1 | — |
| BAD_VALUE | — | Requirements | 8 | 1 | — |
| BAD_VALUE | — | Requires | 5 | 2 | — |
| BAD_VALUE | — | id | 309 | 21 | — |
| DANGLING_REFERENCE | — | Related | 2 | 1 | — |
| DUPLICATE_ID | — | — | 39 | 1 | — |
| MISSING_FIELD | — | — | 282 | 30 | — |
| MISSING_ID | — | — | 40 | 40 | — |
| UNKNOWN_LABEL | — | 12-Bit Histogram | 1 | 1 |  |
| UNKNOWN_LABEL | — | 2x2 Convolution Algorithm | 1 | 1 | Key Considerations |
| UNKNOWN_LABEL | — | 2x2 Convolution Algorithm (RGGB Pattern) | 1 | 1 | Key Considerations |
| UNKNOWN_LABEL | — | 4x4 Convolution Algorithm | 1 | 1 | Key Considerations |
| UNKNOWN_LABEL | — | 4x4 Convolution Algorithm (RGGB Pattern) | 1 | 1 | Key Considerations |
| UNKNOWN_LABEL | — | AOT-Safe Pattern | 1 | 1 | Key Considerations |
| UNKNOWN_LABEL | — | API Design | 2 | 1 | Key Considerations |
| UNKNOWN_LABEL | — | API Pattern | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Acceptance Criteria | 2 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Additional Types | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Algorithm Reference | 1 | 1 | Key Considerations |
| UNKNOWN_LABEL | — | Algorithm Reuse | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Algorithm Similarity | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Architectural Decision | 1 | 1 |  |
| UNKNOWN_LABEL | — | Architecture | 1 | 1 | Requirements; Architecture Decisions; Design Documents; Work Items; External References |
| UNKNOWN_LABEL | — | Audit Trail Semantics | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Available | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Available | 2 | 2 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Bayer-Specific Pixel Selection | 1 | 1 |  |
| UNKNOWN_LABEL | — | Behavior | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Behavior | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Benchmark Configuration | 1 | 1 | Acceptance Criteria; Test Evidence |
| UNKNOWN_LABEL | — | Blocks | 2 | 1 | Requires; Related |
| UNKNOWN_LABEL | — | Bright-Spot Detection Use Case | 1 | 1 |  |
| UNKNOWN_LABEL | — | Bug Report | 1 | 1 |  |
| UNKNOWN_LABEL | — | Bug Report | 1 | 1 | Requirements; Architecture Decisions; Design Documents; Work Items; External References |
| UNKNOWN_LABEL | — | CRITICAL | 3 | 2 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Cache Key Format | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Caching | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Calculation | 1 | 1 | Key Considerations |
| UNKNOWN_LABEL | — | Capture Result Accessors | 1 | 1 |  |
| UNKNOWN_LABEL | — | CaptureResultTypeRegistry Delegation | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | CaptureResultTypeRegistry Integration | 1 | 1 | Key Considerations |
| UNKNOWN_LABEL | — | Channel Naming Examples | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Clone Requirements | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Code Files | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Code Reuse | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Columns | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Component | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Configuration | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Configuration lifecycle by level | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Cons | 10 | 2 | ID; Title; Status |
| UNKNOWN_LABEL | — | Consequences | 5 | 5 | ID; Title; Status |
| UNKNOWN_LABEL | — | Consistency | 2 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Constraint | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Container Types | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Context | 4 | 2 | ID; Title; Status |
| UNKNOWN_LABEL | — | Correction Impact | 1 | 1 |  |
| UNKNOWN_LABEL | — | Covers ADRs | 21 | 21 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Covers Design | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Covers Requirements | 22 | 22 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Created | 32 | 23 | ID; Title; Status |
| UNKNOWN_LABEL | — | Cross-Camera Portability Pattern (CRITICAL) | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Cross-Reference | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Cross-References | 2 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Current Performance | 1 | 1 |  |
| UNKNOWN_LABEL | — | Current Practice | 1 | 1 |  |
| UNKNOWN_LABEL | — | Current Reality | 1 | 1 |  |
| UNKNOWN_LABEL | — | DEPRECATION NOTICE | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Date | 7 | 4 | ID; Title; Status |
| UNKNOWN_LABEL | — | Date | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Deciders | 2 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Decision | 5 | 5 | ID; Title; Status |
| UNKNOWN_LABEL | — | Decision Date | 107 | 31 | ID; Title; Status |
| UNKNOWN_LABEL | — | Decision Date | 37 | 37 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Decision author | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Default Single-Threaded Strategy (Normal Imaging) | 1 | 1 |  |
| UNKNOWN_LABEL | — | Deferred to Phase 3+ | 2 | 1 |  |
| UNKNOWN_LABEL | — | Delete | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Dependencies | 2 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Depends On | 9 | 9 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Deprecation Note | 2 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Description | 10 | 2 | ID; Title; Status |
| UNKNOWN_LABEL | — | Deserialization | 2 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Design | 1 | 1 | Requirements; Architecture Decisions; Design Documents; Work Items; External References |
| UNKNOWN_LABEL | — | Design Completion | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Design Decision | 2 | 1 |  |
| UNKNOWN_LABEL | — | Design ID | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Detection Logic (Reuse from Phase 1) | 1 | 1 | Key Considerations |
| UNKNOWN_LABEL | — | Disposal Control Requirements | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Disposal Tracking Pattern | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Distinction from Setup Properties | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Document ID | 6 | 6 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Document Type | 4 | 4 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Documentation Requirement | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Documentation Requirements | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Domain | 4 | 4 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Enables | 1 | 1 | Requires; Related |
| UNKNOWN_LABEL | — | Enum Aliases (for backward compatibility) | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Example Registration Pattern | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Example Scenario | 1 | 1 |  |
| UNKNOWN_LABEL | — | Examples | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Factory Methods | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Fix | 1 | 1 |  |
| UNKNOWN_LABEL | — | Fix Applied | 1 | 1 | Key Considerations |
| UNKNOWN_LABEL | — | Format Migration | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Frame Rate Justification | 1 | 1 |  |
| UNKNOWN_LABEL | — | Freeze Behavior | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Functional | 2 | 2 | ID; Title; Status |
| UNKNOWN_LABEL | — | Generated Code Pattern | 1 | 1 | Key Considerations |
| UNKNOWN_LABEL | — | Gpixels/sec metric advantages | 1 | 1 |  |
| UNKNOWN_LABEL | — | Historical Context | 2 | 2 |  |
| UNKNOWN_LABEL | — | Historical Context | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Historical Context | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | ID Range | 16 | 16 | ID; Title; Status |
| UNKNOWN_LABEL | — | IDictionarySerializer Interface | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | IMetadataKey Interface | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Immutability Requirements | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Implementation | 2 | 2 | ID; Title; Status |
| UNKNOWN_LABEL | — | Implementation Approach | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Implementation Note | 1 | 1 | Acceptance Criteria; Test Evidence |
| UNKNOWN_LABEL | — | Implementation Note — "Not In Setup" diagnostic string (Issue 16) | 1 | 1 | Acceptance Criteria; Test Evidence |
| UNKNOWN_LABEL | — | Implementation Note — skip detection and CalibrationSkipReason | 1 | 1 | Acceptance Criteria; Test Evidence |
| UNKNOWN_LABEL | — | Implementation Notes | 3 | 2 | ID; Title; Status |
| UNKNOWN_LABEL | — | Implementation guidance | 1 | 1 | Acceptance Criteria; Test Evidence |
| UNKNOWN_LABEL | — | Implemented In | 1 | 1 | Requires; Related |
| UNKNOWN_LABEL | — | Indexing | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Inheritance from REQ-CAL-5200 | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Inheritance from REQ-CAL-5204 | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Inheritance from REQ-CAL-5205 | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Inheritance from REQ-CAL-5220 | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Initial Result Types | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Interface Contract | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Interface Definition | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Interface Inheritance | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Invalid Registration Examples | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Isolation Rules | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Key Concepts | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | L1 Cache Analysis | 1 | 1 |  |
| UNKNOWN_LABEL | — | Language Features to Leverage | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Last Updated | 32 | 23 | ID; Title; Status |
| UNKNOWN_LABEL | — | Legacy Consistency | 1 | 1 |  |
| UNKNOWN_LABEL | — | Lock-Free Read Pattern | 1 | 1 | Key Considerations |
| UNKNOWN_LABEL | — | MUST NOT statements | 4 | 3 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | MUST statements | 2 | 2 | ID; Title; Status |
| UNKNOWN_LABEL | — | MUST statements | 211 | 20 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | MUST statements (Inherited) | 2 | 2 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | MUST statements (Minimum Requirements) | 2 | 2 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Maintainability | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Mathematical Definition | 3 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Memory Efficiency | 3 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Metadata Retrieval | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Metadata Write | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Methods | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Migration Strategies | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Modification Attempts on Frozen Collections | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Multi-Threaded Exception (Auto-Exposure/Auto-HDR Contexts) | 1 | 1 |  |
| UNKNOWN_LABEL | — | NOT acceptable | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Negative | 4 | 2 | ID; Title; Status |
| UNKNOWN_LABEL | — | No Output Image | 1 | 1 |  |
| UNKNOWN_LABEL | — | No Padding | 1 | 1 |  |
| UNKNOWN_LABEL | — | Non-standard calibrations (opt-in model) | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Note | 6 | 6 |  |
| UNKNOWN_LABEL | — | Note | 8 | 3 | Acceptance Criteria; Test Evidence |
| UNKNOWN_LABEL | — | Note | 3 | 3 | ID; Title; Status |
| UNKNOWN_LABEL | — | Note | 2 | 2 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Note | 1 | 1 | Requires; Related |
| UNKNOWN_LABEL | — | Note | 7 | 7 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Note on Flat Field Correction | 1 | 1 | Acceptance Criteria; Test Evidence |
| UNKNOWN_LABEL | — | Note on Temperature | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Nullable Rationale | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Operations | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | OpticalContext Channel Definitions | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | OpticalContext Constants | 1 | 1 |  |
| UNKNOWN_LABEL | — | OpticalContext Requirements | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Optional for MVP | 2 | 2 | Key Considerations |
| UNKNOWN_LABEL | — | Over-Exposure Detection | 1 | 1 |  |
| UNKNOWN_LABEL | — | Owner | 39 | 24 | ID; Title; Status |
| UNKNOWN_LABEL | — | [consumer] ARCHITECTURE (2025-11-02 - ADOPTED) | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Package Information | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Parent Document | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Parent Item | 7 | 7 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Parent Requirement | 2 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Pattern | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Per-Channel Bright-Spot Detection | 1 | 1 |  |
| UNKNOWN_LABEL | — | Percentile-Based Approach | 1 | 1 |  |
| UNKNOWN_LABEL | — | Performance | 5 | 4 | ID; Title; Status |
| UNKNOWN_LABEL | — | Performance Infrastructure | 2 | 2 | ID; Title; Status |
| UNKNOWN_LABEL | — | Performance Infrastructure | 2 | 2 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Performance Optimization | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Performance Targets | 3 | 2 | Acceptance Criteria; Test Evidence |
| UNKNOWN_LABEL | — | Performance Validation | 1 | 1 | Acceptance Criteria; Test Evidence |
| UNKNOWN_LABEL | — | Phase | 10 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Pipeline Semantics | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Platform Requirements | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Positive | 4 | 2 | ID; Title; Status |
| UNKNOWN_LABEL | — | Priority | 13 | 2 | ID; Title; Status |
| UNKNOWN_LABEL | — | ProcessResult Values (from legacy XCore implementation) | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Project | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Project Context | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Properties | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | PropertyTypeRegistry Delegation | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | PropertyTypeRegistry Integration | 1 | 1 | Key Considerations |
| UNKNOWN_LABEL | — | Pros | 10 | 2 | ID; Title; Status |
| UNKNOWN_LABEL | — | Quality | 2 | 2 | ID; Title; Status |
| UNKNOWN_LABEL | — | Rationale | 7 | 6 | ID; Title; Status |
| UNKNOWN_LABEL | — | Read | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Read Operations | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Recommended Data Structure | 1 | 1 | Key Considerations |
| UNKNOWN_LABEL | — | Reference | 1 | 1 | Key Considerations |
| UNKNOWN_LABEL | — | Reference Monochrome Requirement | 1 | 1 |  |
| UNKNOWN_LABEL | — | Registration Requirements | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Registration Rules | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Related | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Related ADRs | 5 | 5 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Related Documents | 3 | 3 | ID; Title; Status |
| UNKNOWN_LABEL | — | Related Documents | 13 | 13 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Related Item | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Related Requirements | 1 | 1 | Acceptance Criteria; Test Evidence |
| UNKNOWN_LABEL | — | Related Requirements | 1 | 1 | Requires; Related |
| UNKNOWN_LABEL | — | Related Requirements | 10 | 10 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Related Work Item | 8 | 8 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Related Work Items | 6 | 6 | ID; Title; Status |
| UNKNOWN_LABEL | — | Related Work Items | 8 | 8 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Release | 1 | 1 | Requirements; Architecture Decisions; Design Documents; Work Items; External References |
| UNKNOWN_LABEL | — | Removal Reason | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Replacement | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Requirement | 2 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Requirements Traceability | 14 | 14 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | RgbFlags Filtering | 1 | 1 |  |
| UNKNOWN_LABEL | — | SHALL statements | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | SHOULD statements | 18 | 8 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | SHOULD statements (Cherry-Pick Strategy) | 4 | 2 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Sensor Coverage | 1 | 1 | Key Considerations |
| UNKNOWN_LABEL | — | Serialization | 2 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | SerializationTypeRegistry API | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Shallow Clone Behavior | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Source Generator Requirements | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Specifically | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Speedup Strategy | 1 | 1 |  |
| UNKNOWN_LABEL | — | Standard Channel Names | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Standard calibrations (opt-out model) | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Standard calibrations requiring advanced user access | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Start Date | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Storage Key | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Superseded By | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Superseded By | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Supersedes | 2 | 2 | ID; Title; Status |
| UNKNOWN_LABEL | — | Supersedes | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Target Date | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Target Performance | 1 | 1 |  |
| UNKNOWN_LABEL | — | Target Release | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Terminology | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Test Cases | 3 | 2 | Acceptance Criteria; Test Evidence |
| UNKNOWN_LABEL | — | Test Coverage | 13 | 1 | Acceptance Criteria; Test Evidence |
| UNKNOWN_LABEL | — | Test Plan | 1 | 1 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Test Plan ID | 22 | 22 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Test Strategy | 2 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Thread Safety Guarantees | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Thread-Local Accumulation (Parallel Mode) | 1 | 1 |  |
| UNKNOWN_LABEL | — | Throughput calculation for `short` data type | 1 | 1 |  |
| UNKNOWN_LABEL | — | ToMutable Behavior | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Trace to | 3 | 2 | ID; Title; Status |
| UNKNOWN_LABEL | — | Trade-off | 1 | 1 |  |
| UNKNOWN_LABEL | — | Type Safety | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | UUID Requirements | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Use Cases | 2 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Valid Registration Examples | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Version | 16 | 16 | ID; Title; Status |
| UNKNOWN_LABEL | — | Version Tracking | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Why Cache-Friendly Architecture | 1 | 1 |  |
| UNKNOWN_LABEL | — | Why Dark Level Subtraction | 1 | 1 |  |
| UNKNOWN_LABEL | — | Why Individual Pixel Storage Prevailed | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Why Not Chosen (Currently) | 1 | 1 | ID; Title; Status |
| UNKNOWN_LABEL | — | Why Rejected | 8 | 2 | ID; Title; Status |
| UNKNOWN_LABEL | — | Why mandatory when coefficients available | 1 | 1 |  |
| UNKNOWN_LABEL | — | Why report both Gpixels/sec and GB/sec | 1 | 1 |  |
| UNKNOWN_LABEL | — | Work Item | 8 | 8 | Status; Version; Created; Last Updated; Owner; ID Range |
| UNKNOWN_LABEL | — | Write | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_LABEL | — | Write Operations | 1 | 1 | MUST Statements; SHOULD Statements; MUST NOT Statements |
| UNKNOWN_SECTION | — | 1. Context | 6 | 6 | Related Documents |
| UNKNOWN_SECTION | — | 1. Purpose | 3 | 3 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 10.2 Architecture Validation | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 11.2 ViewModelBase Auto-Marshalling | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 12.2 Pattern Recognition | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 2. Decision | 6 | 6 | Related Documents |
| UNKNOWN_SECTION | — | 2. Scope | 3 | 3 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 2.2 ViewModel Layer Requirements | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 2.3 Model Layer Requirements | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 3. Functional Requirements | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 3. Parent/Child Landscape | 2 | 2 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 3. Rationale | 6 | 6 | Related Documents |
| UNKNOWN_SECTION | — | 3.2 Hybrid DI Strategy | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 4. Consequences | 6 | 6 | Related Documents |
| UNKNOWN_SECTION | — | 4. Functional Requirements | 2 | 2 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 4. Non-Functional Requirements | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 4.2 Message Processing | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 5. Alternatives Considered | 6 | 6 | Related Documents |
| UNKNOWN_SECTION | — | 5. Non-Functional Requirements | 2 | 2 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 5. Open Questions | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 5.2 Task Cancellation and Cleanup | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 6. Discovery Integration | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 6. Open Questions | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 6. Related Docs | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | 6. Related Documents | 3 | 3 | Related Documents |
| UNKNOWN_SECTION | — | 6. Related Requirements & Documents | 2 | 2 | Related Documents |
| UNKNOWN_SECTION | — | 6.2 Performance Requirements | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 7. Encoding Requirements (Calibration-Specific) | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 7. Next Steps | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 7. Open Items | 5 | 5 | Related Documents |
| UNKNOWN_SECTION | — | 7. Open Questions | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | 7.2 Error Handling | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 8. Open Questions | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 8.2 Testing Support | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 9. Next Steps | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | 9.2 Resource Management | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | AOT Compatibility Strategy | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Acceptance Criteria | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Acceptance Criteria | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Alternatives Considered | 76 | 17 | Related Documents |
| UNKNOWN_SECTION | — | Benefits | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Cache Interface Contract | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Cache Key Format Specification | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Caching Behaviour | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Calibration Type Interface Registry | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Classification Boundary Principle | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Common Error Scenarios | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Consequences | 111 | 23 | Related Documents |
| UNKNOWN_SECTION | — | Context | 114 | 25 | Related Documents |
| UNKNOWN_SECTION | — | Correction Equation | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Cross-References | 8 | 3 | Related Documents |
| UNKNOWN_SECTION | — | Cross-References | 7 | 2 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | DTO Definition | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Decision | 133 | 25 | Related Documents |
| UNKNOWN_SECTION | — | Decisions | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Definitions | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Dependencies (Individual) | 15 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Deprecation Rationale | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Description | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Design Notes | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Discovery Requirements | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Encoding & Storage Notes | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Encoding Requirements | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Examples Across Cache Types | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Existing Pattern (AsyncRamCache.cs:74-77) | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | ForSomeRows Extension Method Specification | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Functional Requirements | 3 | 3 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Future Algorithm Extensions | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Impact Analysis | 17 | 7 | Related Documents |
| UNKNOWN_SECTION | — | Implementation | 34 | 9 | Related Documents |
| UNKNOWN_SECTION | — | Implementation Overview | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Implementation Pattern | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Interactions | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Legacy References | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Memory Pool Integration | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Memory Pool Integration (Bayer-Specific) | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Migration Note | 7 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Migration Notes | 2 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Next Steps | 3 | 3 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Non-Functional Requirements | 3 | 3 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Non-Owning Builder Disposal Behavior | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Open Questions | 3 | 3 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | [consumer] Alternative | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | [consumer] Behavior | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Parent/Child Landscape | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Problem | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Product Applicability (Individual) | 15 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Provider Abstraction Requirements | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Purpose | 3 | 3 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Rationale | 99 | 19 | Related Documents |
| UNKNOWN_SECTION | — | Rationale & Consequences | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Rationale for Deprecation | 2 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Recommended Pattern (Cache-Specific Fetch Methods) | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | References | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Related Decisions | 2 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Related Requirements | 6 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Requirement Statement (Legacy - For Reference Only) | 2 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Requirements | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Row Skipping Pattern (RGGB Bayer Layout) | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Rule [consumer]CAL001: Base Type Registration Prevention | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Rule [consumer]CAL002: Dual Interface Implementation Prohibition | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Runtime SIMD Detection and Dispatch | 1 | 1 | Related Documents |
| UNKNOWN_SECTION | — | Scope | 4 | 4 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Telemetry & Logging | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Test Strategy (Individual) | 15 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Traceability | 2 | 2 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Uncorrectable Pixel Handoff | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Upgrade Requirements | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Validation Criteria | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Validation Method | 1 | 1 | Requirement Statement; Rationale; Success Criteria; Dependencies; Product Applicability; Implementation Notes; Test Strategy; Related Documents |
| UNKNOWN_SECTION | — | Workflow Illustration | 1 | 1 | Related Documents |
