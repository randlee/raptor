# Documentation Reference Notes

These notes exist to satisfy and explain the cross-references used by `rust-development/guidelines.txt`.

## Documentation Has Canonical Sections (M-CANONICAL-DOCS) { #M-CANONICAL-DOCS }

Public-facing and team-facing documentation should use predictable section shapes so readers and agents can locate:
- purpose
- inputs / outputs
- operational constraints
- error behavior
- examples or usage notes

Documentation can be concise, but it should not force readers to infer structure from scattered prose.

## Has Comprehensive Module Documentation (M-MODULE-DOCS) { #M-MODULE-DOCS }

Modules that expose real behavior should document:
- the module's responsibility
- key invariants or ownership boundaries
- important cross-module dependencies
- how callers are expected to use the module correctly

Do not leave significant modules as undocumented implementation buckets.
