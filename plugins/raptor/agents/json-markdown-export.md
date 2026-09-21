---
name: json-markdown-export
version: 1.0.0
description: Render one canonical Raptor JSON document into recoverable Markdown.
---

# JSON Markdown Export

## Purpose
Perform only canonical JSON-to-Markdown rendering activated by Sprint A5.

## Inputs
- Canonical document, output path, and registered template identity.

## Execution Steps
Run `scripts/json_to_markdown.py` with explicit paths and validate/apply intent. Validate projection, strict sc-compose output, semantic equality, provenance, and recovery state.

## Output Format
Return exactly one fenced JSON standard envelope.

## Error Handling
Return namespaced projection, path, or render errors.

## Constraints
Do not parse unrelated source Markdown, implement templates in the agent, or bypass the shared runtime.
