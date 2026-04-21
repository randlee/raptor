# Library UX Reference Notes

These notes provide the referenced anchors used by the Rust development guidelines.

## Errors are Canonical Structs (M-ERRORS-CANONICAL-STRUCTS) { #M-ERRORS-CANONICAL-STRUCTS }

When an error shape is part of a reusable library contract, prefer a stable, named error type with explicit fields over ad hoc tuples, strings, or opaque wrapper noise.

The intent is:
- predictable machine-readable structure
- stable downstream handling
- contextual fields that are worth carrying across crate boundaries

## Complex Type Construction has Builders (M-INIT-BUILDER) { #M-INIT-BUILDER }

When a type has many optional settings, invariants, or construction branches, use a builder instead of a long constructor or loosely structured configuration tuple.

The builder should:
- keep required vs optional fields clear
- validate invariants before construction
- remain ergonomic for the common path
