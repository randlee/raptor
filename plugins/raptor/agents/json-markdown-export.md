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
Validate projection and provenance, then perform the bounded render operation.

## Output Format
Return exactly one fenced JSON standard envelope.

## Error Handling
Return namespaced projection, path, or render errors.

## Constraints
Do not parse source Markdown, persist SQLite, or operate before A5 activation.
