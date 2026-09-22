# Sprint A6 — Repository scan configuration

## Objective

Define the Raptor-owned, versioned authorization boundary that determines which
repository files a scan may inspect. This sprint does not add filesystem
traversal, artifact-family routing, parser selection, or consumer conventions.

## Deliverables

| ID | Deliverable |
|---|---|
| A6-D1 | Public Pydantic models for `.raptor/sources.toml`. |
| A6-D2 | Generated `repository-scan-config.schema.json`. |
| A6-D3 | Normative field, glob, containment, and inventory-order requirements. |
| A6-D4 | Model and JSON Schema tests using only Raptor-owned identifiers and neutral repository paths. |
| A6-D5 | Updated deterministic plugin vendor containing the public configuration model. |

## Acceptance criteria

| ID | Criterion |
|---|---|
| A6-AC1 | Missing, empty, or invalid configuration authorizes no scan; there is no implicit repository-wide fallback. |
| A6-AC2 | Source roots are normalized repository-relative directories and cannot overlap. |
| A6-AC3 | Include and exclude filters use one documented case-sensitive POSIX glob dialect on every platform; exclusion wins. |
| A6-AC4 | Unknown fields, duplicate names, duplicate roots, duplicate patterns, traversal, absolute paths, negation, and unsupported glob syntax fail validation. |
| A6-AC5 | Files outside configured roots, excluded files, and unmatched files are unauthorized. |
| A6-AC6 | Raptor documentation, fixtures, tests, and examples contain no external-consumer names or categories. |
| A6-AC7 | Schema and plugin suites, strict typing, schema drift, vendor drift, and repository-wide forbidden-content checks pass. |

## Authoritative validation

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=schema/src python3 -m pytest schema/tests
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=schema/src python3 -m mypy --strict schema/src/raptor_schema schema/tests/typing/protocol_contract.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=schema/src python3 -m raptor_schema.generate --check --output schema/json/v2
PYTHONDONTWRITEBYTECODE=1 python3 plugins/raptor/scripts/vendor_schema.py --check
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest plugins/raptor/tests
rg -n -i --hidden --glob '!.git/**' --glob '!.sc/**' '[p]3' . && exit 1 || true
```

## Deferred configuration

- artifact-family and document-type routing;
- source-profile and parser selection;
- lifecycle, section, measurement, and identifier mappings;
- template-set and output-path selection;
- filesystem traversal and command integration.
