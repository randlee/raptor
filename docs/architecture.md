# Architecture

Phase A is a short-lived import bridge for the Rust product. It records the
existing documentation-index shape, loads it into development SQLite, and renders
reviewable Markdown. It does not define the product database or a Python runtime.

`schema/record.py` is the authoritative Pydantic v2 model for an extracted
record. `schema/record.schema.json` is its committed JSON Schema output. The
extractor emits JSON, the loader places its top-level fields in `artifacts` and
its links in `relationships`, and the renderer uses one Jinja2 template per item
type.

The scripts are deliberately standalone: no package, configuration system,
plugin, provenance model, transaction log, or code generation is part of this
bridge. Source repositories are corrected by an agent before importing rather
than by adding repository-specific parsing rules here.
