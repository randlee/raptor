# Sprint A8 — Repository configuration manifest

## Objective

Define `.raptor/raptor.toml` as the sole explicit entrypoint for repository
identity and the versioned scan, routing, and identity configuration artifacts.

## Acceptance criteria

| ID | Criterion |
|---|---|
| A8-AC1 | The root manifest requires repository ID and explicit scan, routing, and identity paths. |
| A8-AC2 | Paths are unique, normalized, relative to `.raptor/`, traversal-safe, and carry the required `.toml` or `.json` type. |
| A8-AC3 | Repository manifest and identity manifest IDs must match. |
| A8-AC4 | Missing or invalid configuration never triggers conventional-filename or repository-wide fallback. |
| A8-AC5 | Pydantic, JSON Schema, public exports, vendor, documentation, neutrality, and independent QA gates pass. |

## Deferred

- filesystem loading and atomic configuration snapshots;
- profile installation and trust;
- lifecycle, section, measurement, and identifier mappings;
- template and output materialization policy.
