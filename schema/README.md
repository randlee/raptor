# raptor-schema

`raptor-schema` is Raptor's consumer-neutral canonical artifact contract. It
contains Pydantic v2 models, reference validation, canonical JSON helpers,
identity-manifest validation, and the source-profile protocol. It contains no
Markdown parser, persistence adapter, or client plugin.

```python
from raptor_schema import load_canonical_json, validate_document

document = validate_document(load_canonical_json(payload))
```

Regenerate or verify versioned schemas from the repository root:

```sh
python -m raptor_schema.generate --output schema/json/v1
python -m raptor_schema.generate --check --output schema/json/v1
```

Canonical JSON is UTF-8-compatible text with sorted keys, compact separators,
omitted `None` fields, emitted defaults, and one trailing newline. Authorial
lists retain order; relationships and set-like key lists are normalized by model
validators.

## Compatibility boundary

External adapters construct the public `SourceProfile` boundary types and return
`SourceDocument`. Consumer parsing conventions and fixtures remain in the
consumer. Schema major `1` is supported; other majors fail validation.

Generated JSON Schema expresses structural JSON constraints. Runtime-only checks
include cross-document reference existence, duplicate composite keys, source-root
containment, identity registration conflicts, Python float finiteness, exact
Python scalar distinctions in measurement ranges, and range ordering. Profile
discovery, trust, descriptor I/O, and dynamic loading belong to the later plugin
runtime and are intentionally absent here.
